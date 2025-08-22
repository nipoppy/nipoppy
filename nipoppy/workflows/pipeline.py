"""Base class for pipeline workflows."""

from __future__ import annotations

import json
import re
import shlex
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Iterable, Optional, Tuple, Type

import bids
import pandas as pd
from jinja2 import Environment, meta
from packaging.version import Version
from pydantic import ValidationError
from pysqa import QueueAdapter

from nipoppy.config.boutiques import (
    BoutiquesConfig,
    get_boutiques_config_from_descriptor,
)
from nipoppy.config.hpc import HpcConfig
from nipoppy.config.pipeline import (
    BasePipelineConfig,
    BidsPipelineConfig,
    ExtractionPipelineConfig,
    ProcPipelineConfig,
)
from nipoppy.config.pipeline_step import AnalysisLevelType, ProcPipelineStepConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    FAKE_SESSION_ID,
    LogColor,
    PipelineTypeEnum,
    ReturnCode,
    StrOrPathLike,
)
from nipoppy.layout import DatasetLayout
from nipoppy.utils import (
    FPATH_HPC_TEMPLATE,
    add_pybids_ignore_patterns,
    apply_substitutions_to_json,
    check_participant_id,
    check_session_id,
    create_bids_db,
    get_pipeline_tag,
    load_json,
    participant_id_to_bids_participant_id,
    process_template_str,
    session_id_to_bids_session_id,
)
from nipoppy.workflows.base import BaseDatasetWorkflow


def apply_analysis_level(
    participants_sessions: Iterable[str, str],
    analysis_level: AnalysisLevelType,
) -> Tuple[str, str]:
    """Filter participant-session pairs to run based on the analysis level."""
    if analysis_level == AnalysisLevelType.group:
        return [(None, None)]

    elif analysis_level == AnalysisLevelType.participant:
        participants = []
        for participant, _ in participants_sessions:
            if participant not in participants:
                participants.append(participant)
        return [(participant, None) for participant in participants]

    elif analysis_level == AnalysisLevelType.session:
        sessions = []
        for _, session in participants_sessions:
            if session not in sessions:
                sessions.append(session)
        return [(None, session) for session in sessions]

    else:
        return participants_sessions


def get_pipeline_version(
    pipeline_name: str,
    dpath_pipelines: StrOrPathLike,
) -> str:
    """Get the latest version associated with a pipeline.

    Parameters
    ----------
    pipeline_name : str
        Name of the pipeline, as specified in the config
    dpath_pipelines : nipoppy.env.StrOrPathLike
        Path to directory containing pipeline bundle subdirectories

    Returns
    -------
    str
        The pipeline version
    """
    installed_pipelines = []
    pipeline_config_latest = None
    for fpath_pipeline_config in Path(dpath_pipelines).glob(
        f"*/{DatasetLayout.fname_pipeline_config}"
    ):
        pipeline_config = BasePipelineConfig(**load_json(fpath_pipeline_config))
        if pipeline_config.NAME == pipeline_name:
            if pipeline_config_latest is None:
                pipeline_config_latest = pipeline_config
            elif Version(pipeline_config.VERSION) > Version(
                pipeline_config_latest.VERSION
            ):
                pipeline_config_latest = pipeline_config
        installed_pipelines.append((pipeline_config.NAME, pipeline_config.VERSION))

    if pipeline_config_latest is not None:
        return pipeline_config_latest.VERSION
    else:
        raise ValueError(
            f"No config found for pipeline with NAME={pipeline_name}"
            ". Installed pipelines: "
            + ", ".join(f"{name} {version}" for name, version in installed_pipelines)
        )


class BasePipelineWorkflow(BaseDatasetWorkflow, ABC):
    """A workflow for a pipeline that has a Boutiques descriptor."""

    dname_hpc_logs = "hpc"
    fname_hpc_error = "pysqa.err"
    fname_job_script = "run_queue.sh"

    _pipeline_type = PipelineTypeEnum.PROCESSING

    _pipeline_type_to_pipeline_class_map = {
        PipelineTypeEnum.PROCESSING: ProcPipelineConfig,
        PipelineTypeEnum.BIDSIFICATION: BidsPipelineConfig,
        PipelineTypeEnum.EXTRACTION: ExtractionPipelineConfig,
    }

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        name: str,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        use_list: Optional[StrOrPathLike] = None,
        hpc: Optional[str] = None,
        write_list: Optional[StrOrPathLike] = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run=False,
    ):
        if hpc and write_list:
            raise ValueError(
                "HPC job submission and writing a list of participants and sessions "
                "are mutually exclusive."
            )

        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version
        self.pipeline_step = pipeline_step
        self.participant_id = check_participant_id(participant_id)
        self.session_id = check_session_id(session_id)
        self.use_list = use_list
        self.hpc = hpc
        self.write_list = write_list

        super().__init__(
            dpath_root=dpath_root,
            name=name,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

        # the message logged in run_cleanup will depend on
        # the final values for these attributes (updated in run_main)
        self.n_success = 0
        self.n_total = 0

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return []

    @cached_property
    def dpath_pipeline(self) -> Path:
        """Return the path to the pipeline's derivatives directory."""
        return self.layout.get_dpath_pipeline(
            pipeline_name=self.pipeline_name, pipeline_version=self.pipeline_version
        )

    @cached_property
    def dpath_pipeline_output(self) -> Path:
        """Return the path to the pipeline's output directory."""
        return self.layout.get_dpath_pipeline_output(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
        )

    @cached_property
    def dpath_pipeline_work(self) -> Path:
        """Return the path to the pipeline's working directory."""
        return self.layout.get_dpath_pipeline_work(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            participant_id=self.participant_id,
            session_id=self.session_id,
        )

    @cached_property
    def dpath_pipeline_bids_db(self) -> Path:
        """Return the path to the pipeline's BIDS database directory."""
        return self.layout.get_dpath_pybids_db(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            participant_id=self.participant_id,
            session_id=self.session_id,
        )

    @cached_property
    def dpath_pipeline_bundle(self) -> Path:
        """Path to the pipeline bundle directory."""
        return self.layout.get_dpath_pipeline_bundle(
            self._pipeline_type,
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
        )

    @cached_property
    def pipeline_config(self) -> ProcPipelineConfig:
        """Get the user config object for the processing pipeline."""
        return self._get_pipeline_config(
            self.dpath_pipeline_bundle,
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            pipeline_class=self._pipeline_type_to_pipeline_class_map[
                self._pipeline_type
            ],
        )

    @cached_property
    def pipeline_step_config(self) -> ProcPipelineStepConfig:
        """Get the user config for the pipeline step."""
        return self.pipeline_config.get_step_config(step_name=self.pipeline_step)

    @cached_property
    def fpath_container(self) -> Path:
        """Return the full path to the pipeline's container."""
        fpath_container = self.pipeline_config.get_fpath_container()
        if fpath_container is None:
            raise RuntimeError(
                f"No container image file specified in config for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )

        elif not fpath_container.exists():
            error_message = (
                f"No container image file found at {fpath_container} for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
            if self.pipeline_config.CONTAINER_INFO.URI is not None:
                error_message += (
                    ". This file can be downloaded to the appropriate path by running "
                    "the following command:"
                    f"\n\n{self.pipeline_step_config.CONTAINER_CONFIG.COMMAND.value} "
                    f"pull {self.pipeline_config.CONTAINER_INFO.FILE} "
                    f"{self.pipeline_config.CONTAINER_INFO.URI}"
                )
            raise FileNotFoundError(error_message)
        return fpath_container

    @cached_property
    def descriptor(self) -> dict:
        """Load the pipeline step's Boutiques descriptor."""
        if (fname_descriptor := self.pipeline_step_config.DESCRIPTOR_FILE) is None:
            raise ValueError(
                "No descriptor file specified for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
        fpath_descriptor = self.dpath_pipeline_bundle / fname_descriptor
        self.logger.info(f"Loading descriptor from {fpath_descriptor}")
        descriptor = load_json(fpath_descriptor)
        descriptor = self.config.apply_pipeline_variables(
            pipeline_type=self.pipeline_config.PIPELINE_TYPE,
            pipeline_name=self.pipeline_config.NAME,
            pipeline_version=self.pipeline_config.VERSION,
            json_obj=descriptor,
        )
        return descriptor

    @cached_property
    def invocation(self) -> dict:
        """Load the pipeline step's Boutiques invocation."""
        if (fname_invocation := self.pipeline_step_config.INVOCATION_FILE) is None:
            raise ValueError(
                "No invocation file specified for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
        fpath_invocation = self.dpath_pipeline_bundle / fname_invocation
        self.logger.info(f"Loading invocation from {fpath_invocation}")
        invocation = load_json(fpath_invocation)

        invocation = self.config.apply_pipeline_variables(
            pipeline_type=self.pipeline_config.PIPELINE_TYPE,
            pipeline_name=self.pipeline_config.NAME,
            pipeline_version=self.pipeline_config.VERSION,
            json_obj=invocation,
        )
        return invocation

    @cached_property
    def tracker_config(self) -> TrackerConfig:
        """Load the pipeline step's tracker configuration."""
        if (
            fname_tracker_config := self.pipeline_step_config.TRACKER_CONFIG_FILE
        ) is None:
            raise ValueError(
                f"No tracker config file specified for pipeline {self.pipeline_name}"
                f" {self.pipeline_version}"
            )
        fpath_tracker_config = self.dpath_pipeline_bundle / fname_tracker_config
        self.logger.info(f"Loading tracker config from {fpath_tracker_config}")
        return TrackerConfig(**load_json(fpath_tracker_config))

    @cached_property
    def pybids_ignore_patterns(self) -> list[str]:
        """
        Load the pipeline step's PyBIDS ignore pattern list.

        Note: this does not apply any substitutions, since the subject/session
        patterns are always added.
        """
        # no file specified
        if (
            fname_pybids_ignore := self.pipeline_step_config.PYBIDS_IGNORE_FILE
        ) is None:
            return []

        fpath_pybids_ignore = self.dpath_pipeline_bundle / fname_pybids_ignore

        # load patterns from file
        self.logger.info(f"Loading PyBIDS ignore patterns from {fpath_pybids_ignore}")
        patterns = load_json(fpath_pybids_ignore)

        # validate format
        if not isinstance(patterns, list):
            raise ValueError(
                f"Expected a list of strings in {fpath_pybids_ignore}"
                f", got {patterns} ({type(patterns)})"
            )

        return [re.compile(pattern) for pattern in patterns]

    @cached_property
    def hpc_config(self) -> HpcConfig:
        """Load the pipeline step's HPC configuration."""
        if (fname_hpc_config := self.pipeline_step_config.HPC_CONFIG_FILE) is None:
            data = {}
        else:
            fpath_hpc_config = self.dpath_pipeline_bundle / fname_hpc_config
            self.logger.info(f"Loading HPC config from {fpath_hpc_config}")
            data = self.process_template_json(load_json(fpath_hpc_config))
        return HpcConfig(**data)

    @cached_property
    def boutiques_config(self):
        """Get the Boutiques configuration."""
        try:
            boutiques_config = get_boutiques_config_from_descriptor(
                self.descriptor,
            )
        except ValidationError as exception:
            error_message = str(exception) + str(exception.errors())
            raise ValueError(
                f"Error when loading the Boutiques config from descriptor"
                f": {error_message}"
            )
        except RuntimeError as exception:
            self.logger.debug(
                "Caught exception when trying to load Boutiques config"
                f": {type(exception).__name__}: {exception}"
            )
            self.logger.debug(
                "Assuming Boutiques config is not in descriptor. Using default"
            )
            return BoutiquesConfig()

        self.logger.info(f"Loaded Boutiques config from descriptor: {boutiques_config}")
        return boutiques_config

    def _get_pipeline_config(
        self,
        dpath_pipeline_bundle: Path,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_class: Type[BasePipelineConfig],
    ) -> BasePipelineConfig:
        """Get the config for a pipeline."""
        fpath_config = dpath_pipeline_bundle / self.layout.fname_pipeline_config
        if not fpath_config.exists():
            raise FileNotFoundError(
                f"Pipeline config file not found at {fpath_config} for "
                f"pipeline: {pipeline_name} {pipeline_version}"
            )

        # NOTE: user-defined substitutions take precedence over the pipeline variables
        pipeline_config_json = self.config.apply_pipeline_variables(
            pipeline_type=self._pipeline_type,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            json_obj=self.process_template_json(
                load_json(fpath_config),
            ),
        )

        pipeline_config = pipeline_class(**pipeline_config_json)

        # make sure the config is for the correct pipeline
        if not (
            pipeline_config.NAME == pipeline_name
            and pipeline_config.VERSION == pipeline_version
        ):
            raise RuntimeError(
                f'Expected pipeline config to have NAME="{pipeline_name}" '
                f'and VERSION="{pipeline_version}", got "{pipeline_config.NAME}" and '
                f'"{pipeline_config.VERSION}" instead'
            )

        return self.config.propagate_container_config_to_pipeline(pipeline_config)

    def process_template_json(
        self,
        template_json: dict,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        bids_participant_id: Optional[str] = None,
        bids_session_id: Optional[str] = None,
        objs: Optional[list] = None,
        return_str: bool = False,
        with_substitutions: bool = True,
        **kwargs,
    ):
        """Replace template strings in a JSON object."""
        if with_substitutions:
            # apply user-defined substitutions to maintain compatibility with older
            # pipeline config files that do not use the new pipeline variables
            template_json = apply_substitutions_to_json(
                template_json, self.config.SUBSTITUTIONS
            )
        if participant_id is not None:
            if bids_participant_id is None:
                bids_participant_id = participant_id_to_bids_participant_id(
                    participant_id
                )
            kwargs["participant_id"] = participant_id
            kwargs["bids_participant_id"] = bids_participant_id

        if session_id is not None:
            if bids_session_id is None:
                bids_session_id = session_id_to_bids_session_id(session_id)
            kwargs["session_id"] = session_id
            kwargs["bids_session_id"] = bids_session_id

        if objs is None:
            objs = []
        objs.extend([self, self.layout])

        if kwargs:
            self.logger.debug("Available replacement strings: ")
            max_len = max(len(k) for k in kwargs)
            for k, v in kwargs.items():
                self.logger.debug(f"\t{k}:".ljust(max_len + 3) + v)
            self.logger.debug(f"\t+ all attributes in: {objs}")

        template_json_str = process_template_str(
            json.dumps(template_json),
            objs=objs,
            **kwargs,
        )

        return template_json_str if return_str else json.loads(template_json_str)

    def set_up_bids_db(
        self,
        dpath_pybids_db: StrOrPathLike,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bids.BIDSLayout:
        """Set up the BIDS database."""
        dpath_pybids_db: Path = Path(dpath_pybids_db)

        pybids_ignore_patterns = self.pybids_ignore_patterns.copy()

        if participant_id is not None:
            add_pybids_ignore_patterns(
                current=pybids_ignore_patterns,
                new=f"^(?!/{BIDS_SUBJECT_PREFIX}({participant_id}))",
            )
        if (session_id is not None) and (session_id != FAKE_SESSION_ID):
            add_pybids_ignore_patterns(
                current=pybids_ignore_patterns,
                new=f".*?/{BIDS_SESSION_PREFIX}(?!{session_id})",
            )

        self.logger.info(
            f"Building BIDSLayout with {len(pybids_ignore_patterns)} ignore "
            f"patterns: {pybids_ignore_patterns}"
        )

        if dpath_pybids_db.exists() and list(dpath_pybids_db.iterdir()):
            self.logger.warning(
                f"Overwriting existing BIDS database directory: {dpath_pybids_db}"
            )

        self.logger.debug(f"Path to BIDS data: {self.layout.dpath_bids}")
        bids_layout: bids.BIDSLayout = create_bids_db(
            dpath_bids=self.layout.dpath_bids,
            dpath_pybids_db=dpath_pybids_db,
            ignore_patterns=pybids_ignore_patterns,
            reset_database=True,
        )

        # list all the files in BIDSLayout
        # since we are selecting for specific a specific subject and
        # session, there should not be too many files
        filenames = bids_layout.get(return_type="filename")
        self.logger.debug(f"Found {len(filenames)} files in BIDS database:")
        for filename in filenames:
            self.logger.debug(filename)

        if len(filenames) == 0:
            self.logger.warning("BIDS database is empty")

        return bids_layout

    def check_dir(self, dpath: Path):
        """Create directory if it does not exist."""
        if not dpath.exists():
            self.mkdir(dpath)

    def check_pipeline_version(self):
        """Set the pipeline version based on the config if it is not given."""
        if self.pipeline_version is None:
            self.pipeline_version = get_pipeline_version(
                pipeline_name=self.pipeline_name,
                dpath_pipelines=self.layout.get_dpath_pipeline_store(
                    self._pipeline_type
                ),
            )
            self.logger.warning(
                f"Pipeline version not specified, using version {self.pipeline_version}"
            )

    def _check_pipeline_variables(self):
        """Check that the pipeline variables are not null in the config."""
        for name, value in self.config.PIPELINE_VARIABLES.get_variables(
            self._pipeline_type, self.pipeline_name, self.pipeline_version
        ).items():
            if value is None:
                raise ValueError(
                    f"Variable {name} is not set in the config for pipeline "
                    f"{self.pipeline_name}, version {self.pipeline_version}. You need "
                    "to set it in the PIPELINE_VARIABLES section of the config file at "
                    f"{self.layout.fpath_config}"
                )

    def check_pipeline_step(self):
        """Set the pipeline step name based on the config if it is not given."""
        if self.pipeline_step is None:
            self.pipeline_step = self.pipeline_step_config.NAME
            self.logger.warning(
                f"Pipeline step not specified, using step {self.pipeline_step}"
            )

    def run_setup(self):
        """Run pipeline setup."""
        to_return = super().run_setup()

        self.check_pipeline_version()
        self._check_pipeline_variables()
        self.check_pipeline_step()

        for dpath in self.dpaths_to_check:
            self.check_dir(dpath)

        return to_return

    def run_main(self):
        """Run the pipeline."""
        participants_sessions = self.get_participants_sessions_to_run(
            self.participant_id, self.session_id
        )

        if self.use_list is not None:
            try:
                df_participants_sessions = pd.read_csv(
                    self.use_list, header=None, sep="\t", dtype=str
                )
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Participant-session list file {self.use_list} not found"
                )
            except pd.errors.EmptyDataError:
                raise RuntimeError(
                    f"Participant-session list file {self.use_list} is empty"
                )

            participants_sessions = set(participants_sessions) & set(
                df_participants_sessions.itertuples(index=False, name=None)
            )

        participants_sessions = apply_analysis_level(
            participants_sessions=participants_sessions,
            analysis_level=self.pipeline_step_config.ANALYSIS_LEVEL,
        )

        if self.write_list is not None:
            if not self.dry_run:
                pd.DataFrame(participants_sessions).to_csv(
                    self.write_list, header=False, index=False, sep="\t"
                )
            self.logger.info(f"Wrote participant-session list to {self.write_list}")
        elif self.hpc:
            self._submit_hpc_job(participants_sessions)
        else:
            for participant_id, session_id in participants_sessions:
                self.n_total += 1
                self.logger.info(
                    f"Running for participant {participant_id}, session {session_id}"
                )
                try:
                    self.run_single(participant_id, session_id)
                    self.n_success += 1
                except Exception as exception:
                    self.return_code = ReturnCode.PARTIAL_SUCCESS
                    self.logger.error(
                        f"Error running {self.pipeline_name} {self.pipeline_version}"
                        f" on participant {participant_id}, session {session_id}"
                        f": {exception}"
                    )

    def _generate_cli_command_for_hpc(
        self, participant_id=None, session_id=None
    ) -> list[str]:
        """Generate the CLI command to be run on the HPC cluster."""
        raise NotImplementedError("This method should be implemented in a subclass")

    def _check_hpc_config(self) -> dict:
        """
        Get HPC configuration values to be passed to Jinja template.

        This function logs a warning if the HPC config does not exist (or is empty) or
        if it contains variables that are not defined in the template job script.
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

    def _submit_hpc_job(self, participants_sessions):
        """Submit jobs to a HPC cluster for processing."""
        # make sure HPC directory exists
        dpath_hpc_configs = self.layout.dpath_hpc
        if not (dpath_hpc_configs.exists() and dpath_hpc_configs.is_dir()):
            raise FileNotFoundError(
                "The HPC directory with appropriate content needs to exist at "
                f"{self.layout.dpath_hpc} if HPC job submission is requested"
            )

        qa = QueueAdapter(directory=str(self.layout.dpath_hpc))

        try:
            qa.switch_cluster(self.hpc)
        except KeyError:
            raise ValueError(
                f"Invalid HPC cluster type: {self.hpc}"
                f". Available clusters are: {qa.list_clusters()}"
            )

        # generate the list of nipoppy commands for a shell array
        job_array_commands = []
        participant_ids = []
        session_ids = []
        for participant_id, session_id in participants_sessions:
            command = self._generate_cli_command_for_hpc(
                participant_id=participant_id, session_id=session_id
            )
            job_array_commands.append(shlex.join(command))
            participant_ids.append(participant_id)
            session_ids.append(session_id)
            self.n_total += 1  # for logging in run_cleanup()

        # skip if there are no jobs to submit
        if len(job_array_commands) == 0:
            return

        job_name = get_pipeline_tag(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            pipeline_step=self.pipeline_step,
            participant_id=self.participant_id,
            session_id=self.session_id,
        )
        dpath_work = self.dpath_pipeline_work

        # this is the file that will be created by PySQA
        # if the job submission command fails
        # first we delete it to make sure it is not already there
        fpath_hpc_error = dpath_work / self.fname_hpc_error
        fpath_hpc_error.unlink(missing_ok=True)

        # create the HPC logs directory
        dpath_hpc_logs = self.layout.dpath_logs / self.dname_hpc_logs
        dpath_hpc_logs.mkdir(parents=True, exist_ok=True)

        # user-defined args
        job_args = self._check_hpc_config()

        job_id = None
        if not self.dry_run:
            job_id = qa.submit_job(
                queue=self.hpc,
                working_directory=str(dpath_work),
                command="",  # not used in default template but cannot be None
                cores=0,  # not used in default template but cannot be None
                NIPOPPY_HPC=self.hpc,
                NIPOPPY_JOB_NAME=job_name,
                NIPOPPY_DPATH_LOGS=dpath_hpc_logs,
                NIPOPPY_HPC_PREAMBLE_STRINGS=self.config.HPC_PREAMBLE,
                NIPOPPY_COMMANDS=job_array_commands,
                NIPOPPY_DPATH_ROOT=self.layout.dpath_root,
                NIPOPPY_PIPELINE_NAME=self.pipeline_name,
                NIPOPPY_PIPELINE_VERSION=self.pipeline_version,
                NIPOPPY_PIPELINE_STEP=self.pipeline_step,
                NIPOPPY_PARTICIPANT_IDS=participant_ids,
                NIPOPPY_SESSION_IDS=session_ids,
                **job_args,
            )

        fpath_job_script = dpath_work / self.fname_job_script
        if fpath_job_script.exists():
            self.logger.info(f"Job script created at {fpath_job_script}")
        else:
            self.logger.warning(f"No job script found at {fpath_job_script}.")

        # raise error if an error file was created
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

        # for logging in run_cleanup()
        self.n_success += len(job_array_commands)

    def run_cleanup(self):
        """Log a summary message."""
        if self.n_total == 0:
            self.logger.warning(
                "No participants or sessions to run. Make sure there are no mistakes "
                "in the input arguments, the dataset's manifest or config file, and/or "
                f"check the curation status file at {self.layout.fpath_curation_status}"
            )
            self.return_code = ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN
        elif self.hpc is not None:
            if self.n_success == 0:
                self.logger.error(f"[{LogColor.FAILURE}]Failed to submit HPC jobs[/]")
            else:
                self.logger.info(
                    f"[{LogColor.SUCCESS}]Successfully submitted {self.n_success} "
                    "HPC job(s)[/]"
                )
        else:
            if self.pipeline_step_config.ANALYSIS_LEVEL == AnalysisLevelType.group:
                log_msg = "Ran on the entire study"
            else:
                log_msg = (
                    f"Ran for {self.n_success} out of "
                    f"{self.n_total} participants or sessions"
                )

            if self.n_success == 0:
                self.logger.error(log_msg)
            elif self.n_success == self.n_total:
                self.logger.success(log_msg)
            else:
                self.logger.warning(log_msg)

        return super().run_cleanup()

    @abstractmethod
    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """
        Return participant-session pairs to loop over with run_single().

        This is an abstract method that should be defined explicitly in subclasses.
        """

    @abstractmethod
    def run_single(self, participant_id: Optional[str], session_id: Optional[str]):
        """
        Run on a single participant/session.

        This is an abstract method that should be defined explicitly in subclasses.
        """

    def generate_fpath_log(
        self,
        dnames_parent: Optional[str | list[str]] = None,
        fname_stem: Optional[str] = None,
    ) -> Path:
        """Generate a log file path."""
        # make sure that pipeline version is not None
        self.check_pipeline_version()
        if dnames_parent is None:
            dnames_parent = get_pipeline_tag(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
            )
        if fname_stem is None:
            fname_stem = get_pipeline_tag(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
                participant_id=self.participant_id,
                session_id=self.session_id,
            )
        return super().generate_fpath_log(
            dnames_parent=dnames_parent, fname_stem=fname_stem
        )
