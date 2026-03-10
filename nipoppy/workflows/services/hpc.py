"""HPC runner service."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from jinja2 import Environment, meta
from pysqa import QueueAdapter

from nipoppy.config.hpc import HpcConfig
from nipoppy.env import PROGRAM_NAME, StrOrPathLike
from nipoppy.exceptions import LayoutError, WorkflowError
from nipoppy.logger import get_logger
from nipoppy.utils.utils import FPATH_HPC_TEMPLATE

if TYPE_CHECKING:
    from nipoppy.study import Study

logger = get_logger()


class HPCRunner:
    """
    Service for generating and submitting HPC jobs via PySQA.

    Parameters
    ----------
    context : Study
        The shared workflow context containing layout, logger, and config.
    hpc_config : HpcConfig
        The HPC-specific configuration.
    """

    def __init__(self, context: Study, hpc_config: Optional[HpcConfig] = None):
        self.context = context
        self.hpc_config = hpc_config

    @staticmethod
    def generate_cli_command(
        subcommand: str,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        keep_workdir: bool = False,
        extra_flags: Optional[list[str]] = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
    ) -> list[str]:
        """
        Generate the CLI command to be run on the HPC cluster for a participant/session.

        Skips the --simulate, --hpc, --write-list and --dry-run options.

        Parameters
        ----------
        subcommand : str
            The nipoppy CLI subcommand (e.g. "bidsify", "process", "extract").
        dpath_root : StrOrPathLike
            Path to the dataset root directory.
        pipeline_name : str
            Name of the pipeline to run.
        pipeline_version : str, optional
            Version of the pipeline.
        pipeline_step : str, optional
            Step of the pipeline.
        participant_id : str, optional
            Participant ID to run on.
        session_id : str, optional
            Session ID to run on.
        keep_workdir : bool, optional
            Whether to keep the working directory after the run.
        extra_flags : list[str], optional
            Additional CLI flags to append after ``--keep-workdir`` and before
            ``--layout``.
        fpath_layout : StrOrPathLike, optional
            Path to a custom layout file.
        verbose : bool, optional
            Whether to enable verbose output.

        Returns
        -------
        list[str]
            The CLI command as a list of string tokens.
        """
        command = [
            PROGRAM_NAME,
            subcommand,
            "--dataset",
            dpath_root,
            "--pipeline",
            pipeline_name,
        ]
        if pipeline_version is not None:
            command.extend(["--pipeline-version", pipeline_version])
        if pipeline_step is not None:
            command.extend(["--pipeline-step", pipeline_step])
        if participant_id is not None:
            command.extend(["--participant-id", participant_id])
        if session_id is not None:
            command.extend(["--session-id", session_id])
        if keep_workdir:
            command.append("--keep-workdir")
        if extra_flags:
            command.extend(extra_flags)
        if fpath_layout:
            command.extend(["--layout", fpath_layout])
        if verbose:
            command.append("--verbose")
        return [str(c) for c in command]

    def _check_hpc_config(self) -> dict:
        """
        Get HPC configuration values to be passed to Jinja template.

        This function logs a warning if the HPC config does not exist (or is empty) or
        if it contains variables that are not defined in the template job script.
        """
        if not self.hpc_config:
            logger.warning("HPC configuration is empty")
            return {}

        job_args = self.hpc_config.model_dump()
        if len(job_args) == 0:
            logger.warning("HPC configuration is empty")

        template_ast = Environment().parse(FPATH_HPC_TEMPLATE.read_text())
        template_vars = meta.find_undeclared_variables(template_ast)
        missing_vars = set(job_args.keys()) - template_vars
        if len(missing_vars) > 0:
            logger.warning(
                "Found variables in the HPC config that are not used in the template "
                f"job script: {missing_vars}. Update the config or modify the template "
                f"at {FPATH_HPC_TEMPLATE}."
            )

        return job_args

    def submit(
        self,
        hpc_cluster: str,
        job_name: str,
        job_array_commands: list,
        participant_ids: list,
        session_ids: list,
        dpath_work: Path,
        dpath_hpc_logs: Path,
        fname_hpc_error: str,
        fname_job_script: str,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_step: str,
        dry_run: bool = False,
    ) -> Optional[int]:
        """
        Submit a job to the HPC scheduler.

        Parameters
        ----------
        hpc_cluster : str
            The name of the HPC cluster configuration to use.
        job_name : str
            Name of the job to submit.
        job_array_commands : list
            List of commands to run.
        participant_ids : list
            List of participant IDs associated with the job.
        session_ids : list
            List of session IDs associated with the job.
        dpath_work : Path
            Working directory for the job.
        dpath_hpc_logs : Path
            Directory where HPC logs will be saved.
        fname_hpc_error : str
            Filename of the HPC error log.
        fname_job_script : str
            Filename of the job script to generate.
        pipeline_name : str
            Name of the pipeline being run.
        pipeline_version : str
            Version of the pipeline being run.
        pipeline_step : str
            Step of the pipeline being run.
        dry_run : bool, optional
            Whether to only generate the script without submitting, by default False.

        Returns
        -------
        int or None
            The job ID if submitted successfully, else None.
        """
        dpath_hpc_configs = self.context.layout.dpath_hpc
        if not (dpath_hpc_configs.exists() and dpath_hpc_configs.is_dir()):
            raise LayoutError(
                "The HPC directory with appropriate content needs to exist at "
                f"{self.context.layout.dpath_hpc} if HPC job submission is requested"
            )

        qa = QueueAdapter(directory=str(self.context.layout.dpath_hpc))

        try:
            qa.switch_cluster(hpc_cluster)
        except KeyError as e:
            raise WorkflowError(
                f"Invalid HPC cluster type: {hpc_cluster}"
                f". Available clusters are: {qa.list_clusters()}"
            ) from e

        # this is the file that will be created by PySQA
        # if the job submission command fails
        fpath_hpc_error = dpath_work / fname_hpc_error
        fpath_hpc_error.unlink(missing_ok=True)

        dpath_hpc_logs.mkdir(parents=True, exist_ok=True)

        job_args = self._check_hpc_config()

        job_id = None
        if not dry_run:
            job_id = qa.submit_job(
                queue=hpc_cluster,
                working_directory=str(dpath_work),
                command="",  # not used in default template but cannot be None
                cores=0,  # not used in default template but cannot be None
                NIPOPPY_HPC=hpc_cluster,
                NIPOPPY_JOB_NAME=job_name,
                NIPOPPY_DPATH_LOGS=dpath_hpc_logs,
                NIPOPPY_HPC_PREAMBLE_STRINGS=self.context.config.HPC_PREAMBLE,
                NIPOPPY_COMMANDS=job_array_commands,
                NIPOPPY_DPATH_ROOT=self.context.layout.dpath_root,
                NIPOPPY_PIPELINE_NAME=pipeline_name,
                NIPOPPY_PIPELINE_VERSION=pipeline_version,
                NIPOPPY_PIPELINE_STEP=pipeline_step,
                NIPOPPY_PARTICIPANT_IDS=participant_ids,
                NIPOPPY_SESSION_IDS=session_ids,
                **job_args,
            )

        fpath_job_script = dpath_work / fname_job_script
        if fpath_job_script.exists():
            logger.info(f"Job script created at {fpath_job_script}")
        else:
            logger.warning(f"No job script found at {fpath_job_script}.")

        if fpath_hpc_error.exists():
            raise WorkflowError(
                "Error occurred while submitting the HPC job:"
                f"\n{fpath_hpc_error.read_text()}"
                f"\nThe job script can be found at {fpath_job_script}."
                "\nThis file is auto-generated. To modify it, you will need to "
                "modify the pipeline's HPC configuration in the config file and/or "
                f"the template job script in {self.context.layout.dpath_hpc}."
            )

        if job_id is not None:
            logger.info(f"HPC job ID: {job_id}")

        return job_id
