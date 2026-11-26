"""Executor that submits work items as jobs to an HPC cluster."""

from __future__ import annotations

import shlex

from nipoppy.config.hpc import HpcConfig
from nipoppy.exceptions import ReturnCode
from nipoppy.logger import get_logger
from nipoppy.utils.utils import get_pipeline_tag, load_json
from nipoppy.workflows.executor import ExecutionResult, Executor, WorkItem
from nipoppy.workflows.runner import Runner
from nipoppy.workflows.services.hpc import HPCRunner

logger = get_logger()


class HPCExecutor(Executor[None]):
    """Submit work items as an array job to an HPC cluster.

    The workflow's attributes are read lazily in ``execute()``, so they are only
    valid after the workflow's ``run_setup``. The executor reads the pipeline
    config, bundle path, Boutiques template processing and the CLI command
    (``generate_cli_command``) from the workflow.

    The workflow's ``__init__`` rejects the combination of an HPC executor with
    ``write_subcohort``, so the executor is never used when a subcohort is written.
    """

    def __init__(
        self,
        workflow: Runner,
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

    def execute(self, items: list[WorkItem]) -> ExecutionResult[None]:
        """Submit the work items to the HPC cluster."""
        workflow = self.workflow

        if not items:
            return ExecutionResult(
                ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN, [], []
            )

        # generate the list of nipoppy commands for a shell array
        job_array_commands = []
        participant_ids = []
        session_ids = []
        for item in items:
            command = workflow.generate_cli_command(
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
            dpath_hpc_logs=workflow.study.layout.dpath_logs / "hpc",
            pipeline_name=workflow.pipeline_name,
            pipeline_version=workflow.pipeline_version,
            pipeline_step=workflow.pipeline_step,
            dry_run=workflow.dry_run,
        )

        # Not all jobs have necessarily been submitted.
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
