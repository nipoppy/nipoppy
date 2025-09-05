"""Workflow for pipeline validate command."""

import logging
from pathlib import Path

from nipoppy.env import StrOrPathLike
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.workflows.base import BaseWorkflow


class PipelineValidateWorkflow(BaseWorkflow):
    """Workflow for pipeline validate command."""

    def __init__(
        self,
        pipeline_dir: StrOrPathLike,
        verbose=False,
        dry_run=False,
    ):
        super().__init__(
            _name="pipeline_validate",
            verbose=verbose,
            dry_run=dry_run,
        )
        self.pipeline_dir = Path(pipeline_dir)

    def run_main(self):
        """Run the main workflow."""
        self.logger.info(f"Validating pipeline at {self.pipeline_dir}")
        check_pipeline_bundle(
            self.pipeline_dir, logger=self.logger, log_level=logging.INFO
        )

        self.logger.success("The pipeline files are all valid")
