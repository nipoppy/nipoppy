"""Workflow for pipeline validate command."""

import logging
from pathlib import Path
from typing import Optional

from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.pipeline_store.validation import check_pipeline_bundle
from nipoppy.workflows.base import BaseWorkflow


class PipelineValidateWorkflow(BaseWorkflow):
    """Workflow for pipeline validate command."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        dpath_pipeline: StrOrPathLike,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose=False,
        dry_run=False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name="pipeline_validate",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logging=True,
        )
        self.dpath_pipeline = Path(dpath_pipeline)

    def run_main(self):
        """Run the main workflow."""
        self.logger.info(f"Validating pipeline at {self.dpath_pipeline}")
        check_pipeline_bundle(
            self.dpath_pipeline,
            substitution_objs=[self, self.layout],
            logger=self.logger,
            log_level=logging.INFO,
        )

        self.logger.info(
            f"[{LogColor.SUCCESS}]The pipeline files are all valid![/]",
        )
