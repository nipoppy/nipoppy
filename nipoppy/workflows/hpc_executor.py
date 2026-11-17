"""Executor that submits work items as jobs to an HPC cluster."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any, Protocol

from nipoppy.config.hpc import HpcConfig
from nipoppy.config.pipeline_step import ProcPipelineStepConfig
from nipoppy.env import PROGRAM_NAME, StrOrPathLike
from nipoppy.exceptions import ReturnCode
from nipoppy.logger import get_logger
from nipoppy.study import Study
from nipoppy.utils.utils import get_pipeline_tag, load_json
from nipoppy.workflows.executor import ExecutionResult, Executor, WorkItem
from nipoppy.workflows.services.hpc import HPCRunner

logger = get_logger()


class HPCWorkflowContext(Protocol):
    """The narrow view of a pipeline workflow that is needed to submit HPC jobs.

    The members are read only inside ``HPCExecutor.execute()`` (and
    ``generate_cli_command()``), and are valid only after the workflow's
    ``run_setup``.

    This is a two-way object reference (the workflow holds the executor, and the
    executor holds this narrow view of the workflow), not an import cycle. It
    mirrors the ``work_fn=self.run_single`` callback of ``LocalExecutor`` in
    nipoppy/nipoppy#1224.

    All HPC-specific knowledge stays in this module:
    ``pipeline_step_config.HPC_CONFIG_FILE``, ``study.layout.dpath_hpc`` and
    ``dpath_logs``, and ``study.config.HPC_PREAMBLE`` and ``HPC_QUEUE_LIMIT``.
    """

    subcommand: str
    dpath_root: Path
    fpath_layout: StrOrPathLike | None
    pipeline_name: str
    pipeline_version: str | None
    pipeline_step: str | None
    pipeline_step_config: ProcPipelineStepConfig
    dpath_pipeline_bundle: Path
    dpath_pipeline_work: Path
    participant_id: str | None
    session_id: str | None
    keep_workdir: bool
    verbose: bool
    dry_run: bool
    study: Study

    @property
    def extra_cli_flags(self) -> list[str]:
        """Workflow-specific CLI flags to reproduce the run."""
        ...

    def process_template_json(
        self,
        template_json: dict,
        participant_id: str | None = None,
        session_id: str | None = None,
        bids_participant_id: str | None = None,
        bids_session_id: str | None = None,
        objs: list | None = None,
        return_str: bool = False,
        with_substitutions: bool = True,
        **kwargs,
    ):
        """Replace template strings in a JSON object."""
        ...


class HPCExecutor(Executor[None]):
    """Submit work items as an array job to an HPC cluster.

    Nothing is read from the workflow until ``execute()`` or
    ``generate_cli_command()`` is called, since the executor is created before the
    workflow's setup phase.
    """

    def __init__(
        self,
        workflow: HPCWorkflowContext,
        hpc_cluster: str,
    ):
        self.workflow = workflow
        self.hpc_cluster = hpc_cluster

    def _load_hpc_config(self) -> HpcConfig:
        """Load the pipeline step's HPC configuration."""
        workflow = self.workflow
        fname_hpc_config = workflow.pipeline_step_config.HPC_CONFIG_FILE
        if fname_hpc_config is None:
            data = {}
        else:
            fpath_hpc_config = workflow.dpath_pipeline_bundle / fname_hpc_config
            logger.info(f"Loading HPC config from {fpath_hpc_config}")
            data = workflow.process_template_json(
                load_json(fpath_hpc_config, allow_json5=True)
            )
        return HpcConfig(**data)

    def _build_hpc_runner(self, hpc_config: HpcConfig) -> HPCRunner:
        """Build the HPC runner service."""
        workflow = self.workflow
        return HPCRunner(
            hpc_cluster=self.hpc_cluster,
            hpc_config=hpc_config,
            dpath_root=workflow.dpath_root,
            dpath_hpc=workflow.study.layout.dpath_hpc,
            preamble=workflow.study.config.HPC_PREAMBLE,
            queue_limit=workflow.study.config.HPC_QUEUE_LIMIT,
        )

    def generate_cli_command(
        self,
        participant_id: str | None,
        session_id: str | None,
    ) -> list[str]:
        """Generate the CLI command for a participant-session combination.

        Skips the --simulate, --hpc, --write-subcohort and --dry-run options.
        Appends the workflow's ``extra_cli_flags`` to the command.

        Parameters
        ----------
        participant_id : str, optional
            Participant ID to run on.
        session_id : str, optional
            Session ID to run on.

        Returns
        -------
        list[str]
            The CLI command as a list of string tokens.
        """
        workflow = self.workflow
        command: list[str] = [
            PROGRAM_NAME,
            workflow.subcommand,
            "--study",
            str(workflow.dpath_root),
            "--pipeline",
            workflow.pipeline_name,
        ]
        default_options: dict[str, Any] = {
            "--pipeline-version": workflow.pipeline_version,
            "--pipeline-step": workflow.pipeline_step,
            "--layout": workflow.fpath_layout,
            "--participant-id": participant_id,
            "--session-id": session_id,
        }
        for option, value in default_options.items():
            if value is not None:
                command.extend([option, str(value)])

        if workflow.keep_workdir:
            command.append("--keep-workdir")
        if workflow.verbose:
            command.append("--verbose")

        for flag in workflow.extra_cli_flags:
            if flag in command:
                raise ValueError(
                    f"Flag {flag} is already in the command and cannot be overridden "
                    "via extra_cli_flags."
                )
            command.append(flag)

        return [str(c) for c in command]

    def execute(self, items: list[WorkItem]) -> ExecutionResult[None]:
        """Submit the work items to the HPC cluster."""
        workflow = self.workflow

        if not items:
            # the workflow logs the "no participants or sessions" warning
            return ExecutionResult(
                ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN, [], []
            )

        # generate the list of nipoppy commands for a shell array
        job_array_commands = []
        participant_ids = []
        session_ids = []
        for item in items:
            command = self.generate_cli_command(
                participant_id=item.participant_id, session_id=item.session_id
            )
            job_array_commands.append(shlex.join(command))
            participant_ids.append(item.participant_id)
            session_ids.append(item.session_id)

        job_name = get_pipeline_tag(
            pipeline_name=workflow.pipeline_name,
            pipeline_version=workflow.pipeline_version,
            pipeline_step=workflow.pipeline_step,
            participant_id=workflow.participant_id,
            session_id=workflow.session_id,
        )

        hpc_runner = self._build_hpc_runner(self._load_hpc_config())
        n_submitted = hpc_runner.submit(
            job_name=job_name,
            job_array_commands=job_array_commands,
            participant_ids=participant_ids,
            session_ids=session_ids,
            dpath_work=workflow.dpath_pipeline_work,
            # HPC job logs go in <logs>/hpc
            dpath_hpc_logs=workflow.study.layout.dpath_logs / "hpc",
            pipeline_name=workflow.pipeline_name,
            pipeline_version=workflow.pipeline_version,
            pipeline_step=workflow.pipeline_step,
            dry_run=workflow.dry_run,
        )

        # HPCRunner.submit submits only the first N commands (in order) when the
        # queue limit applies and returns N; see its docstring for the contract.
        successful = items[:n_submitted]
        failed = items[n_submitted:]

        n_total = len(items)
        if n_submitted == 0:
            return_code = ReturnCode.FAILURE
            logger.failure("Failed to submit HPC jobs")
        elif n_submitted < n_total:
            return_code = ReturnCode.PARTIAL_SUCCESS
            logger.warning(
                f"Submitted {n_submitted} out of {n_total} HPC job(s); "
                "the HPC queue limit was reached"
            )
        else:
            return_code = ReturnCode.SUCCESS
            logger.success(f"Successfully submitted {n_submitted} HPC job(s)")

        return ExecutionResult(return_code, successful, failed)
