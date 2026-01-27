"""Workflow for pipeline validate command."""

import logging
from pathlib import Path

from nipoppy.env import StrOrPathLike
from nipoppy.logger import get_logger
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.workflows.base import Workflow

logger = get_logger()


class PipelineValidateWorkflow(Workflow):
    """Workflow for pipeline validate command."""

    def __init__(
        self,
        dpath_pipeline: StrOrPathLike,
        verbose=False,
        dry_run=False,
    ):
        super().__init__(
            name="pipeline_validate",
            verbose=verbose,
            dry_run=dry_run,
        )
        self.dpath_pipeline = Path(dpath_pipeline)

    def run_main(self):
        """Run the main workflow."""
        logger.info(f"Validating pipeline at {self.dpath_pipeline}")
        check_pipeline_bundle(self.dpath_pipeline, log_level=logging.INFO)

        logger.success("The pipeline files are all valid")
