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

    # the pipeline can be something that is applied to an entire dataset
    # or something that is applied to a single subject/session

    # needs attributes
    # dpath_pipeline
    # dpath_pipeline_output
    # dpath_pipeline_work

    def __init__(
        self,
        dpath_root: Path | str,
        pipeline_name: str,
        pipeline_version: str,
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

    @cached_property
    def pipeline_config(self) -> PipelineConfig:
        self.config.get_pipeline_config(self.pipeline_name, self.pipeline_version)

    def run_main(self, subject=None, session=None):
        for subject, session in self.get_subjects_sessions_to_run(subject, session):
            self.run_single(subject, session)

    def get_subjects_sessions_to_run(
        self, subject: Optional[str], session: Optional[str]
    ):
        # need to decide whether to check the manifest or the doughnut (or the bagel)
        # need a way to select the column of the doughnut
        pass

    @abstractmethod
    def run_single(self, subject: str, session: str):
        """Run on a single subject/session."""
        pass


class PipelineRunner(_PipelineWorkflow):
    """Pipeline runner."""

    def run_single(self, subject: str, session: str):
        """Run on a single subject/session."""
        pass


class PipelineTracker(_PipelineWorkflow):
    """Pipeline tracker."""

    def run_single(self, subject: str, session: str):
        """Run on a single subject/session."""
        pass
