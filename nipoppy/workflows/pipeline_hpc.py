"""HPC job submission functionality for pipeline workflows."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Tuple

from jinja2 import Environment, meta
from pysqa import QueueAdapter

from nipoppy.utils.utils import FPATH_HPC_TEMPLATE, get_pipeline_tag

if TYPE_CHECKING:
    from nipoppy.config.hpc import HpcConfig
    from nipoppy.layout import DatasetLayout
    from nipoppy.logger import NipoppyLogger


class PipelineHpcSubmitter:
    """Handles HPC job submission for pipeline workflows."""

    fname_hpc_error = "pysqa.err"
    fname_job_script = "run_queue.sh"
    dname_hpc_logs = "hpc"

    def __init__(
        self,
        layout: DatasetLayout,
        logger: NipoppyLogger,
        hpc_config: HpcConfig,
        hpc_preamble: list[str],
        dry_run: bool = False,
    ):
        """Initialize the HPC submitter.

        Parameters
        ----------
        layout : DatasetLayout
            Dataset layout object
        logger : NipoppyLogger
            Logger instance
        hpc_config : HpcConfig
            HPC configuration
        hpc_preamble : list[str]
            HPC preamble strings from config
        dry_run : bool
            Whether to run in dry-run mode
        """
        self.layout = layout
        self.logger = logger
        self.hpc_config = hpc_config
        self.hpc_preamble = hpc_preamble
        self.dry_run = dry_run

    def check_hpc_config(self) -> dict:
        """
        Get HPC configuration values to be passed to Jinja template.

        This function logs a warning if the HPC config does not exist (or is empty) or
        if it contains variables that are not defined in the template job script.

        Returns
        -------
        dict
            HPC configuration as dictionary
        """
        job_args = self.hpc_config.model_dump()
        if len(job_args) == 0:
            self.logger.warning("HPC configuration is empty")

        template_ast = Environment().parse(FPATH_HPC_TEMPLATE.read_text())
        template_vars = meta.find_undeclared_variables(template_ast)
        missing_vars = set(job_args.keys()) - template_vars
        if len(missing_vars) > 0:
            self.logger.warning(
                "Found variables in the HPC config that are not used in the template "
                f"job script: {missing_vars}. Update the config or modify the template "
                f"at {FPATH_HPC_TEMPLATE}."
            )

        return job_args

    def submit_hpc_job(
        self,
        hpc_type: str,
        participants_sessions: Iterable[Tuple[str, str]],
        pipeline_name: str,
        pipeline_version: str,
        pipeline_step: str,
        dpath_work: Path,
        participant_id: str = None,
        session_id: str = None,
        generate_command_func: callable = None,
    ) -> int:
        """Submit jobs to a HPC cluster for processing.

        Parameters
        ----------
        hpc_type : str
            Type of HPC cluster (e.g., 'slurm', 'sge')
        participants_sessions : Iterable[Tuple[str, str]]
            Participant-session pairs to process
        pipeline_name : str
            Name of the pipeline
        pipeline_version : str
            Version of the pipeline
        pipeline_step : str
            Pipeline step name
        dpath_work : Path
            Working directory for the pipeline
        participant_id : str, optional
            Single participant ID (for job naming)
        session_id : str, optional
            Single session ID (for job naming)
        generate_command_func : callable
            Function to generate CLI command for each participant/session pair
            Should accept (participant_id, session_id) and return list[str]

        Returns
        -------
        int
            Number of jobs submitted

        Raises
        ------
        FileNotFoundError
            If HPC directory doesn't exist
        ValueError
            If invalid HPC cluster type
        RuntimeError
            If job submission fails
        """
        # Make sure HPC directory exists
        dpath_hpc_configs = self.layout.dpath_hpc
        if not (dpath_hpc_configs.exists() and dpath_hpc_configs.is_dir()):
            raise FileNotFoundError(
                "The HPC directory with appropriate content needs to exist at "
                f"{self.layout.dpath_hpc} if HPC job submission is requested"
            )

        qa = QueueAdapter(directory=str(self.layout.dpath_hpc))

        try:
            qa.switch_cluster(hpc_type)
        except KeyError:
            raise ValueError(
                f"Invalid HPC cluster type: {hpc_type}"
                f". Available clusters are: {qa.list_clusters()}"
            )

        # Generate the list of nipoppy commands for a shell array
        job_array_commands = []
        participant_ids = []
        session_ids = []
        for part_id, sess_id in participants_sessions:
            command = generate_command_func(
                participant_id=part_id, session_id=sess_id
            )
            job_array_commands.append(shlex.join(command))
            participant_ids.append(part_id)
            session_ids.append(sess_id)

        # Skip if there are no jobs to submit
        if len(job_array_commands) == 0:
            return 0

        job_name = get_pipeline_tag(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant_id=participant_id,
            session_id=session_id,
        )

        # This is the file that will be created by PySQA
        # if the job submission command fails
        # first we delete it to make sure it is not already there
        fpath_hpc_error = dpath_work / self.fname_hpc_error
        fpath_hpc_error.unlink(missing_ok=True)

        # Create the HPC logs directory
        dpath_hpc_logs = self.layout.dpath_logs / self.dname_hpc_logs
        dpath_hpc_logs.mkdir(parents=True, exist_ok=True)

        # User-defined args
        job_args = self.check_hpc_config()

        job_id = None
        if not self.dry_run:
            job_id = qa.submit_job(
                queue=hpc_type,
                working_directory=str(dpath_work),
                command="",  # not used in default template but cannot be None
                cores=0,  # not used in default template but cannot be None
                NIPOPPY_HPC=hpc_type,
                NIPOPPY_JOB_NAME=job_name,
                NIPOPPY_DPATH_LOGS=dpath_hpc_logs,
                NIPOPPY_HPC_PREAMBLE_STRINGS=self.hpc_preamble,
                NIPOPPY_COMMANDS=job_array_commands,
                NIPOPPY_DPATH_ROOT=self.layout.dpath_root,
                NIPOPPY_PIPELINE_NAME=pipeline_name,
                NIPOPPY_PIPELINE_VERSION=pipeline_version,
                NIPOPPY_PIPELINE_STEP=pipeline_step,
                NIPOPPY_PARTICIPANT_IDS=participant_ids,
                NIPOPPY_SESSION_IDS=session_ids,
                **job_args,
            )

        fpath_job_script = dpath_work / self.fname_job_script
        if fpath_job_script.exists():
            self.logger.info(f"Job script created at {fpath_job_script}")
        else:
            self.logger.warning(f"No job script found at {fpath_job_script}.")

        # Raise error if an error file was created
        if fpath_hpc_error.exists():
            raise RuntimeError(
                "Error occurred while submitting the HPC job:"
                f"\n{fpath_hpc_error.read_text()}"
                f"\nThe job script can be found at {fpath_job_script}."
                "\nThis file is auto-generated. To modify it, you will need to "
                "modify the pipeline's HPC configuration in the config file and/or "
                f"the template job script in {self.layout.dpath_hpc}."
            )

        if job_id is not None:
            self.logger.info(f"HPC job ID: {job_id}")

        return len(job_array_commands)
