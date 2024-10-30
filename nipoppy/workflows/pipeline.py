"""Base class for pipeline workflows."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Iterable, Optional, Tuple

import bids
from pydantic import ValidationError

from nipoppy.config.boutiques import (
    BoutiquesConfig,
    get_boutiques_config_from_descriptor,
)
from nipoppy.config.main import get_pipeline_config, get_pipeline_version
from nipoppy.config.pipeline import ProcPipelineConfig
from nipoppy.config.pipeline_step import AnalysisLevelType, ProcPipelineStepConfig
from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    LogColor,
    ReturnCode,
    StrOrPathLike,
)
from nipoppy.utils import (
    add_pybids_ignore_patterns,
    check_participant_id,
    check_session_id,
    create_bids_db,
    get_pipeline_tag,
    load_json,
    participant_id_to_bids_participant,
    process_template_str,
    session_id_to_bids_session,
)
from nipoppy.workflows.base import BaseWorkflow


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


class BasePipelineWorkflow(BaseWorkflow, ABC):
    """A workflow for a pipeline that has a Boutiques descriptor."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        name: str,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        logger: Optional[logging.Logger] = None,
        dry_run=False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name=name,
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version
        self.pipeline_step = pipeline_step
        self.participant_id = check_participant_id(participant_id)
        self.session_id = check_session_id(session_id)

        # the message logged in run_cleanup will depend on
        # the final values for these attributes (updated in run_main)
        self.n_success = 0
        self.n_total = 0

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return [self.dpath_pipeline]

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
        return self.layout.get_dpath_bids_db(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            participant_id=self.participant_id,
            session_id=self.session_id,
        )

    @cached_property
    def _pipeline_configs(self) -> list[ProcPipelineConfig]:
        return self.config.PROC_PIPELINES

    @cached_property
    def pipeline_config(self) -> ProcPipelineConfig:
        """Get the user config for the pipeline."""
        return get_pipeline_config(
            self.pipeline_name, self.pipeline_version, self._pipeline_configs
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
            raise FileNotFoundError(
                f"No container image file found at {fpath_container} for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
        return fpath_container

    @cached_property
    def descriptor(self) -> dict:
        """Load the pipeline step's Boutiques descriptor."""
        fpath_descriptor = self.pipeline_step_config.DESCRIPTOR_FILE
        if fpath_descriptor is None:
            raise ValueError(
                "No descriptor file specified for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
        self.logger.info(f"Loading descriptor from {fpath_descriptor}")
        descriptor = load_json(fpath_descriptor)
        descriptor = self.config.apply_substitutions_to_json(descriptor)
        return descriptor

    @cached_property
    def invocation(self) -> dict:
        """Load the pipeline step's Boutiques invocation."""
        fpath_invocation = self.pipeline_step_config.INVOCATION_FILE
        if fpath_invocation is None:
            raise ValueError(
                "No invocation file specified for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
        self.logger.info(f"Loading invocation from {fpath_invocation}")
        invocation = load_json(fpath_invocation)
        invocation = self.config.apply_substitutions_to_json(invocation)
        return invocation

    @cached_property
    def pybids_ignore_patterns(self) -> list[str]:
        """
        Load the pipeline step's PyBIDS ignore pattern list.

        Note: this does not apply any substitutions, since the subject/session
        patterns are always added.
        """
        fpath_pybids_ignore = self.pipeline_step_config.PYBIDS_IGNORE_FILE

        # no file specified
        if fpath_pybids_ignore is None:
            return []

        # load patterns from file
        patterns = load_json(fpath_pybids_ignore)

        # validate format
        if not isinstance(patterns, list):
            raise ValueError(
                f"Expected a list of strings in {fpath_pybids_ignore}"
                f", got {patterns} ({type(patterns)})"
            )

        return [re.compile(pattern) for pattern in patterns]

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

    def process_template_json(
        self,
        template_json: dict,
        participant_id: Optional[str],
        session_id: Optional[str],
        bids_participant: Optional[str] = None,
        bids_session: Optional[str] = None,
        objs: Optional[list] = None,
        return_str: bool = False,
        **kwargs,
    ):
        """Replace template strings in a JSON object."""
        if participant_id is not None:
            if bids_participant is None:
                bids_participant = participant_id_to_bids_participant(participant_id)
            kwargs["participant_id"] = participant_id
            kwargs["bids_participant"] = bids_participant

        if session_id is not None:
            if bids_session is None:
                bids_session = session_id_to_bids_session(session_id)
            kwargs["session_id"] = session_id
            kwargs["bids_session"] = bids_session

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
        dpath_bids_db: StrOrPathLike,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bids.BIDSLayout:
        """Set up the BIDS database."""
        dpath_bids_db: Path = Path(dpath_bids_db)

        pybids_ignore_patterns = self.pybids_ignore_patterns.copy()

        if participant_id is not None:
            add_pybids_ignore_patterns(
                current=pybids_ignore_patterns,
                new=f"^(?!/{BIDS_SUBJECT_PREFIX}({participant_id}))",
            )
        if session_id is not None:
            add_pybids_ignore_patterns(
                current=pybids_ignore_patterns,
                new=f".*?/{BIDS_SESSION_PREFIX}(?!{session_id})",
            )

        self.logger.info(
            f"Building BIDSLayout with {len(pybids_ignore_patterns)} ignore "
            f"patterns: {pybids_ignore_patterns}"
        )

        if dpath_bids_db.exists() and list(dpath_bids_db.iterdir()):
            self.logger.warning(
                f"Overwriting existing BIDS database directory: {dpath_bids_db}"
            )

        self.logger.debug(f"Path to BIDS data: {self.layout.dpath_bids}")
        bids_layout: bids.BIDSLayout = create_bids_db(
            dpath_bids=self.layout.dpath_bids,
            dpath_bids_db=dpath_bids_db,
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
            self.mkdir(dpath, log_level=logging.WARNING)

    def check_pipeline_version(self):
        """Set the pipeline version based on the config if it is not given."""
        if self.pipeline_version is None:
            self.pipeline_version = get_pipeline_version(
                pipeline_name=self.pipeline_name,
                pipeline_configs=self._pipeline_configs,
            )
            self.logger.warning(
                f"Pipeline version not specified, using version {self.pipeline_version}"
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
        self.check_pipeline_step()

        for dpath in self.dpaths_to_check:
            self.check_dir(dpath)

        return to_return

    def run_main(self):
        """Run the pipeline."""
        participants_sessions = self.get_participants_sessions_to_run(
            self.participant_id, self.session_id
        )

        participants_sessions = apply_analysis_level(
            participants_sessions=participants_sessions,
            analysis_level=self.pipeline_step_config.ANALYSIS_LEVEL,
        )

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

    def run_cleanup(self):
        """Log a summary message."""
        if self.n_total == 0:
            self.logger.warning(
                "No participants or sessions to run. Make sure there are no mistakes "
                "in the input arguments, the dataset's manifest or config file, "
                f"and/or check the doughnut file at {self.layout.fpath_doughnut}"
            )
        else:
            # change the message depending on how successful the run was
            prefix = "Ran"
            suffix = ""
            if self.n_success == 0:
                color = LogColor.FAILURE
            elif self.n_success == self.n_total:
                color = LogColor.SUCCESS
                prefix = f"Successfully {prefix.lower()}"
                suffix = "!"
            else:
                color = LogColor.PARTIAL_SUCCESS

            if self.pipeline_step_config.ANALYSIS_LEVEL == AnalysisLevelType.group:
                message_body = "on the entire study"
            else:
                message_body = (
                    f"for {self.n_success} out of "
                    f"{self.n_total} participants or sessions"
                )

            self.logger.info(f"[{color}]{prefix} {message_body}{suffix}[/]")

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
