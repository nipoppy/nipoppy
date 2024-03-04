"""Base class for pipeline workflows."""

import logging
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Optional

from nipoppy.config import PipelineConfig
from nipoppy.utils import get_pipeline_tag
from nipoppy.workflows.workflow import _Workflow


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
        return self.layout.get_dpath_pipeline(self.pipeline_name, self.pipeline_version)

    @cached_property
    def dpath_pipeline_work(self) -> Path:
        return self.layout.get_dpath_pipeline_work(
            self.pipeline_name, self.pipeline_version
        )

    @cached_property
    def dpath_pipeline_output(self) -> Path:
        return self.layout.get_dpath_pipeline_output(
            self.pipeline_name, self.pipeline_version
        )

    @cached_property
    def pipeline_config(self) -> PipelineConfig:
        self.config.get_pipeline_config(self.pipeline_name, self.pipeline_version)

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
        pass


class PipelineTracker(_PipelineWorkflow):
    """Pipeline tracker."""

    def run_single(self, participant: str, session: str):
        """Run tracker on a single participant/session."""
        pass
