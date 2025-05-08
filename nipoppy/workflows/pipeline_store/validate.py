"""Workflow for pipeline validate command."""

import logging
from pathlib import Path

from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.workflows.base import BaseWorkflow


class PipelineValidateWorkflow(BaseWorkflow):
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
        self.logger.info(f"Validating pipeline at {self.dpath_pipeline}")
        check_pipeline_bundle(
            self.dpath_pipeline, logger=self.logger, log_level=logging.INFO
        )

        self.logger.info(
            f"[{LogColor.SUCCESS}]The pipeline files are all valid![/]",
        )
