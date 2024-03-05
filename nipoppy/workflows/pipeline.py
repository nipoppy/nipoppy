"""Base class for pipeline workflows."""

import json
import logging
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Optional

from boutiques import bosh

from nipoppy.config import PipelineConfig, SingularityConfig
from nipoppy.utils import (
    DPATH_DESCRIPTORS,
    get_pipeline_tag,
    load_json,
    process_template_str,
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
        return self.layout.get_dpath_pipeline(self.pipeline_name, self.pipeline_version)

    @cached_property
    def dpath_pipeline_work(self) -> Path:
        """Return the path to the pipeline's working directory."""
        return self.layout.get_dpath_pipeline_work(
            self.pipeline_name, self.pipeline_version
        )

    @cached_property
    def dpath_pipeline_output(self) -> Path:
        """Return the path to the pipeline's output directory."""
        return self.layout.get_dpath_pipeline_output(
            self.pipeline_name, self.pipeline_version
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
    def container(self) -> Path:
        """Return the full path to the pipeline's container."""
        # TODO
        pass

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

    def run_setup(self, **kwargs):
        """Run pipeline setup."""
        to_return = super().run_setup(**kwargs)

        # create pipeline directories if needed
        for dpath in [
            self.dpath_pipeline,
            self.dpath_pipeline_work,
            self.dpath_pipeline_output,
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
            self.run_single(participant, session)

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


class PipelineRunner(_PipelineWorkflow):
    """Pipeline runner."""

    def run_single(self, participant: str, session: str):
        """Run pipeline on a single participant/session."""
        # process and validate the descriptor
        descriptor_str = process_template_str(
            json.dumps(self.descriptor),
            participant=participant,
            session=session,
            objs=[self, self.layout],
        )
        self.logger.info("Validating the JSON descriptor")
        self.logger.debug(descriptor_str)
        bosh(["validate", descriptor_str])

        # process and validate the invocation
        invocation_str = process_template_str(
            json.dumps(self.invocation),
            participant=participant,
            session=session,
            objs=[self, self.layout],
        )
        self.logger.info("Validating the JSON invocation")
        self.logger.debug(invocation_str)
        bosh(["invocation", "-i", invocation_str, descriptor_str])

        # # print generated command
        # self.run_command(
        #     ["bosh", "exec", "simulate", "-i", invocation_str, descriptor_str]
        # )

        # run
        self.run_command(
            ["bosh", "exec", "launch", "--stream", descriptor_str, invocation_str]
        )

        return descriptor_str, invocation_str


class PipelineTracker(_PipelineWorkflow):
    """Pipeline tracker."""

    def run_single(self, participant: str, session: str):
        """Run tracker on a single participant/session."""
        # get list of paths

        # check status

        # TODO handle potentially zipped archives

        pass
