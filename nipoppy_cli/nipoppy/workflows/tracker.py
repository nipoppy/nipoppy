"""PipelineTracker workflow."""

import logging
from pathlib import Path
from typing import Optional

from nipoppy.tabular.bagel import Bagel
from nipoppy.workflows.pipeline import BasePipelineWorkflow


class PipelineTracker(BasePipelineWorkflow):
    """Pipeline tracker."""

    def __init__(
        self,
        dpath_root: Path | str,
        pipeline_name: str,
        pipeline_version: str,
        participant: str = None,
        session: str = None,
        fpath_layout: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name="track",
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            participant=participant,
            session=session,
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.bagel: Bagel = Bagel()  # may get overwritten

    def run_setup(self, **kwargs):
        """Load/initialize the bagel file."""
        if self.layout.fpath_imaging_bagel.exists():
            self.bagel = Bagel.load(self.layout.fpath_imaging_bagel)
            self.logger.info(
                f"Found existing bagel with shape {self.bagel.shape}"
                f" at {self.layout.fpath_imaging_bagel}"
            )
        else:
            self.bagel = Bagel()
            self.logger.info("Initialized empty bagel")
        return super().run_setup(**kwargs)

    def check_status(self, relative_paths):
        """Check the processing status based on a list of expected paths."""
        for relative_path in relative_paths:
            self.logger.debug(
                f"Checking path {self.dpath_pipeline_output / relative_path}"
            )

            # TODO handle potentially zipped archives
            matches = list(self.dpath_pipeline_output.glob(relative_path))
            self.logger.debug(f"Matches: {matches}")
            if not matches:
                return Bagel.status_fail

        return Bagel.status_success

    def run_single(self, participant: str, session: str):
        """Run tracker on a single participant/session."""
        # get list of paths from global config
        tracker_config = self.process_template_json(
            self.pipeline_config.TRACKER_CONFIG,
            participant=participant,
            session=session,
        )

        # check status and update bagel
        status = self.check_status(tracker_config["pipeline_complete"])
        self.bagel = self.bagel.add_or_update_records(
            {
                Bagel.col_participant_id: participant,
                Bagel.col_session: session,
                Bagel.col_pipeline_name: self.pipeline_name,
                Bagel.col_pipeline_version: self.pipeline_version,
                Bagel.col_pipeline_complete: status,
            }
        )
        return status

    def run_cleanup(self, **kwargs):
        """Save the bagel file."""
        self.logger.info(f"New/updated bagel shape: {self.bagel.shape}")
        self.save_tabular_file(self.bagel, self.layout.fpath_imaging_bagel)
        return super().run_cleanup(**kwargs)
