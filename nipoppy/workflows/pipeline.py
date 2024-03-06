"""Base class for pipeline workflows."""

import json
import logging
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Optional

import bids
from boutiques import bosh

from nipoppy.config import PipelineConfig, SingularityConfig
from nipoppy.utils import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    DPATH_DESCRIPTORS,
    create_bids_db,
    get_pipeline_tag,
    load_json,
    participant_id_to_bids_id,
    process_template_str,
    strip_session,
)
from nipoppy.workflows.base import _Workflow


class _PipelineWorkflow(_Workflow, ABC):
    """A workflow for a pipeline that has a Boutiques descriptor."""

    def __init__(
        self,
        dpath_root: Path | str,
        pipeline_name: str,
        pipeline_version: str,
        participant=None,
        session=None,
        logger: Optional[logging.Logger] = None,
        dry_run=False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name=get_pipeline_tag(pipeline_name, pipeline_version),
            logger=logger,
            dry_run=dry_run,
        )
        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version
        self.participant = participant
        self.session = session

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
            participant=self.participant,
            session=self.session,
        )

    @cached_property
    def dpath_pipeline_bids_db(self) -> Path:
        """Return the path to the pipeline's BIDS database directory."""
        return self.layout.get_dpath_bids_db(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            participant=self.participant,
            session=self.session,
        )

    @cached_property
    def pipeline_config(self) -> PipelineConfig:
        """Get the user config for the pipeline."""
        return self.config.get_pipeline_config(
            self.pipeline_name, self.pipeline_version
        )

    @cached_property
    def singularity_config(self) -> SingularityConfig:
        """Get the Singularity config for the pipeline."""
        return self.pipeline_config.get_singularity_config()

    @property
    def singularity_command(self) -> str:
        """Build the Singularity command to run the pipeline."""
        return self.singularity_config.build_command()

    @cached_property
    def fpath_container(self) -> Path:
        """Return the full path to the pipeline's container."""
        fpath_container = (
            self.layout.dpath_containers / self.pipeline_config.get_container()
        )
        if not fpath_container.exists():
            raise FileNotFoundError(
                f"No container image file found at {fpath_container} for pipeline"
                f" {self.pipeline_name}, version {self.pipeline_version}"
            )
        return fpath_container

    @cached_property
    def descriptor(self) -> dict:
        """Load the pipeline's Boutiques descriptor."""
        # first check if the pipeline config has the descriptor itself
        descriptor = self.pipeline_config.DESCRIPTOR
        if descriptor is None:
            # TODO then check if the pipeline config specifies a path

            # finally check if there is a built-in descriptor
            fpath_descriptor_builtin = DPATH_DESCRIPTORS / f"{self.name}.json"
            try:
                descriptor = load_json(fpath_descriptor_builtin)
                self.logger.info("Using built-in descriptor")
            except FileNotFoundError:
                raise RuntimeError(
                    "No built-in descriptor found for pipeline"
                    f" {self.pipeline_name}, version {self.pipeline_version}"
                    # TODO dump a list of built-in descriptors
                )
        else:
            self.logger.info("Loaded descriptor from pipeline config")
        return descriptor

    @cached_property
    def invocation(self) -> dict:
        """Load the pipeline's Boutiques invocation."""
        # for now just get the invocation directly
        # TODO eventually add option to load from file
        return self.pipeline_config.INVOCATION

    def set_up_bids_db(
        self,
        dpath_bids_db: Path | str,
        participant: Optional[str] = None,
        session: Optional[str] = None,
    ) -> bids.BIDSLayout:
        """Set up the BIDS database."""
        dpath_bids_db = Path(dpath_bids_db)

        if participant is not None:
            self.pipeline_config.add_pybids_ignore_patterns(
                f"^(?!/{BIDS_SUBJECT_PREFIX}({participant}))"
            )
        if session is not None:
            self.pipeline_config.add_pybids_ignore_patterns(
                f".*?/{BIDS_SESSION_PREFIX}(?!{strip_session(session)})"
            )

        pybids_ignore_patterns = self.pipeline_config.PYBIDS_IGNORE
        self.logger.info(
            "Building BIDSLayout with ignore patterns:"
            f" {[str(pattern) for pattern in pybids_ignore_patterns]}"
        )
        self.logger.debug(pybids_ignore_patterns)

        if dpath_bids_db.exists():
            self.logger.warning(
                f"Overwriting existing BIDS database directory: {dpath_bids_db}"
            )

        self.logger.debug(self.layout.dpath_bids)
        bids_layout: bids.BIDSLayout = create_bids_db(
            dpath_bids=self.layout.dpath_bids,
            dpath_bids_db=dpath_bids_db,
            ignore_patterns=pybids_ignore_patterns,
        )

        # list all the files in BIDSLayout
        # since we are selecting for specific a specific subject and
        # session, there should not be too many files
        filenames = bids_layout.get(return_type="filename")
        for filename in filenames:
            self.logger.debug(filename)

        if len(filenames) == 0:
            self.logger.warning("BIDS database is empty")

        return bids_layout

    def run_setup(self, **kwargs):
        """Run pipeline setup."""
        to_return = super().run_setup(**kwargs)

        # create pipeline directories if needed
        for dpath in [
            self.dpath_pipeline,
            self.dpath_pipeline_output,
            self.dpath_pipeline_work,
            self.dpath_pipeline_bids_db,
        ]:
            if not dpath.exists():
                self.logger.warning(
                    f"Creating directory because it does not exist: {dpath}"
                )
                if not self.dry_run:
                    dpath.mkdir(parents=True, exist_ok=True)

        return to_return

    def run_main(self, **kwargs):
        """Run the pipeline."""
        for participant, session in self.get_participants_sessions_to_run(
            self.participant, self.session
        ):
            self.logger.info(
                f"Running {self.pipeline_name} {self.pipeline_version}"
                f" on participant {participant}, session {session}"
            )
            self.run_single(participant, session)

    def run_cleanup(self, **kwargs):
        """Run pipeline cleanup."""
        if self.dpath_pipeline_work.exists():
            self.run_command(["rm", "-rf", self.dpath_pipeline_work])
        return super().run_cleanup(**kwargs)

    def get_participants_sessions_to_run(
        self, participant: Optional[str], session: Optional[str]
    ):
        # TODO add option in Boutiques descriptor of pipeline
        # 1. "manifest" (or "all"?)
        # 2. "downloaded" (from doughnut)
        # 3. "organized" (from doughnut)
        # 4. "converted" (from doughnut)
        # 5. "dataset" (i.e. apply on entire dataset, do not loop over anything)

        # for now just check the participants/sessions that have BIDS data
        return self.doughnut.get_converted_participants_sessions(
            participant=participant, session=session
        )

    @abstractmethod
    def run_single(self, participant: Optional[str], session: Optional[str]):
        """Run on a single participant/session."""
        pass

    def generate_fpath_log(self) -> Path:
        return super().generate_fpath_log(
            fname_stem=get_pipeline_tag(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
                participant=self.participant,
                session=self.session,
            )
        )


class PipelineRunner(_PipelineWorkflow):
    """Pipeline runner."""

    def run_single(self, participant: str, session: str):
        """Run pipeline on a single participant/session."""
        # set up PyBIDS database
        self.set_up_bids_db(
            dpath_bids_db=self.dpath_pipeline_bids_db,
            participant=participant,
            session=session,
        )
        self.singularity_config.add_bind_path(self.dpath_pipeline_bids_db)

        # set up template string replacement
        kwargs = dict(
            participant=participant,
            session=session,
            bids_id=participant_id_to_bids_id(participant),
            session_short=strip_session(session),
        )
        objs = [self, self.layout]
        self.logger.debug("Available replacement strings: ")
        for k, v in kwargs.items():
            self.logger.debug(f"\t{k}: {v}")
        self.logger.debug(f"+ all attributes in: {objs}")

        # process and validate the descriptor
        descriptor_str = process_template_str(
            json.dumps(self.descriptor),
            objs=objs,
            **kwargs,
        )
        self.logger.info("Validating the JSON descriptor")
        self.logger.debug(descriptor_str)
        bosh(["validate", descriptor_str])

        # process and validate the invocation
        invocation_str = process_template_str(
            json.dumps(self.invocation),
            objs=objs,
            **kwargs,
        )
        self.logger.info("Validating the JSON invocation")
        self.logger.debug(invocation_str)
        bosh(["invocation", "-i", invocation_str, descriptor_str])

        # update singularity config
        self.singularity_config.add_bind_path(self.layout.dpath_bids, mode="ro")
        self.singularity_config.add_bind_path(self.dpath_pipeline_output)
        self.singularity_config.add_bind_path(self.dpath_pipeline_work)
        self.logger.info(f"Using Singularity config: {self.singularity_config}")
        self.singularity_config.set_env_vars()

        # run as a subprocess so that stdout/error are captured in the log
        self.run_command(
            ["bosh", "exec", "launch", "--stream", descriptor_str, invocation_str]
        )

        return descriptor_str, invocation_str


class PipelineTracker(_PipelineWorkflow):
    """Pipeline tracker."""

    def run_setup(self, **kwargs):
        """Load/initialize the bagel file."""
        # TODO
        return super().run_setup(**kwargs)

    def run_single(self, participant: str, session: str):
        """Run tracker on a single participant/session."""
        # get list of paths

        # check status and add to bagel file

        # TODO handle potentially zipped archives

        pass

    def run_cleanup(self, **kwargs):
        """Save the bagel file."""
        return super().run_cleanup(**kwargs)
