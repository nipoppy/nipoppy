"""Helper functions for HPC job submission in pipeline workflows.

This module contains extracted helper functions to reduce the size and complexity
of the BasePipelineWorkflow class. These functions handle HPC-specific operations.
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Tuple

from jinja2 import Environment, meta
from pysqa import QueueAdapter

from nipoppy.utils.utils import FPATH_HPC_TEMPLATE, get_pipeline_tag

if TYPE_CHECKING:
    from nipoppy.config.hpc import HpcConfig
    from nipoppy.layout import DatasetLayout
    from nipoppy.logger import NipoppyLogger


def check_hpc_config(hpc_config: HpcConfig, logger: NipoppyLogger) -> dict:
    """
    Get HPC configuration values to be passed to Jinja template.

    This function logs a warning if the HPC config does not exist (or is empty) or
    if it contains variables that are not defined in the template job script.

    Parameters
    ----------
    hpc_config : HpcConfig
        HPC configuration object
    logger : NipoppyLogger
        Logger instance

    Returns
    -------
    dict
        HPC configuration as dictionary
    """
    job_args = hpc_config.model_dump()
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


def submit_hpc_job(
    layout: DatasetLayout,
    logger: NipoppyLogger,
    hpc_type: str,
    hpc_config: HpcConfig,
    participants_sessions: Iterable[Tuple[str, str]],
    pipeline_name: str,
    pipeline_version: str,
    pipeline_step: str,
    participant_id: str,
    session_id: str,
    dpath_work: Path,
    hpc_preamble: list[str],
    generate_command_func: Callable,
    dry_run: bool = False,
    fname_hpc_error: str = "pysqa.err",
    fname_job_script: str = "run_queue.sh",
    dname_hpc_logs: str = "hpc",
) -> int:
    """Submit jobs to a HPC cluster for processing.

    Parameters
    ----------
    layout : DatasetLayout
        Dataset layout object
    logger : NipoppyLogger
        Logger instance
    hpc_type : str
        Type of HPC cluster (e.g., 'slurm', 'sge')
    hpc_config : HpcConfig
        HPC configuration
    participants_sessions : Iterable[Tuple[str, str]]
        Participant-session pairs to process
    pipeline_name : str
        Name of the pipeline
    pipeline_version : str
        Version of the pipeline
    pipeline_step : str
        Pipeline step name
    participant_id : str
        Single participant ID (for job naming)
    session_id : str
        Single session ID (for job naming)
    dpath_work : Path
        Working directory for the pipeline
    hpc_preamble : list[str]
        HPC preamble strings from config
    generate_command_func : Callable
        Function to generate CLI command for each participant/session pair
        Should accept (participant_id, session_id) and return list[str]
    dry_run : bool
        Whether to run in dry-run mode
    fname_hpc_error : str
        Filename for HPC error file
    fname_job_script : str
        Filename for job script
    dname_hpc_logs : str
        Directory name for HPC logs

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
    dpath_hpc_configs = layout.dpath_hpc
    if not (dpath_hpc_configs.exists() and dpath_hpc_configs.is_dir()):
        raise FileNotFoundError(
            "The HPC directory with appropriate content needs to exist at "
            f"{layout.dpath_hpc} if HPC job submission is requested"
        )

    qa = QueueAdapter(directory=str(layout.dpath_hpc))

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
        command = generate_command_func(participant_id=part_id, session_id=sess_id)
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
    fpath_hpc_error = dpath_work / fname_hpc_error
    fpath_hpc_error.unlink(missing_ok=True)

    # Create the HPC logs directory
    dpath_hpc_logs = layout.dpath_logs / dname_hpc_logs
    dpath_hpc_logs.mkdir(parents=True, exist_ok=True)

    # User-defined args
    job_args = check_hpc_config(hpc_config, logger)

    job_id = None
    if not dry_run:
        job_id = qa.submit_job(
            queue=hpc_type,
            working_directory=str(dpath_work),
            command="",  # not used in default template but cannot be None
            cores=0,  # not used in default template but cannot be None
            NIPOPPY_HPC=hpc_type,
            NIPOPPY_JOB_NAME=job_name,
            NIPOPPY_DPATH_LOGS=dpath_hpc_logs,
            NIPOPPY_HPC_PREAMBLE_STRINGS=hpc_preamble,
            NIPOPPY_COMMANDS=job_array_commands,
            NIPOPPY_DPATH_ROOT=layout.dpath_root,
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

    # Raise error if an error file was created
    if fpath_hpc_error.exists():
        raise RuntimeError(
            "Error occurred while submitting the HPC job:"
            f"\n{fpath_hpc_error.read_text()}"
            f"\nThe job script can be found at {fpath_job_script}."
            "\nThis file is auto-generated. To modify it, you will need to "
            "modify the pipeline's HPC configuration in the config file and/or "
            f"the template job script in {layout.dpath_hpc}."
        )

    if job_id is not None:
        logger.info(f"HPC job ID: {job_id}")

    return len(job_array_commands)
