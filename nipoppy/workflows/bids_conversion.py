"""Workflow for convert command."""

import logging
from functools import cached_property
from pathlib import Path
from typing import Optional

from nipoppy.config.pipeline import PipelineConfig
from nipoppy.utils import get_pipeline_tag
from nipoppy.workflows.runner import PipelineRunner


class BidsConversionRunner(PipelineRunner):
    """Convert data to BIDS."""

    def __init__(
        self,
        dpath_root: Path | str,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_step: str,
        participant=None,
        session=None,
        simulate=False,
        logger: Optional[logging.Logger] = None,
        dry_run=False,
    ):
        super().__init__(
            dpath_root,
            pipeline_name,
            pipeline_version,
            participant,
            session,
            simulate,
            logger,
            dry_run,
        )
        self.name = "bids_conversion"
        self.pipeline_step = pipeline_step
        self.dpaths_to_check = []  # do not create any pipeline-specific directory

    @cached_property
    def pipeline_config(self) -> PipelineConfig:
        """Get the user config for the BIDS conversion software."""
        return self.config.get_bids_pipeline_config(
            self.pipeline_name,
            self.pipeline_version,
            self.pipeline_step,
        )

    def get_participants_sessions_to_run(
        self, participant: Optional[str], session: Optional[str]
    ):
        """Return participant-session pairs to run the pipeline on."""
        return self.doughnut.get_organized_participants_sessions(
            participant=participant, session=session
        )

    def run_single(self, participant: str, session: str):
        """Run BIDS conversion on a single participant/session."""
        # get singularity command
        singularity_command = self.process_singularity_config(
            participant=participant,
            session=session,
            bind_paths=[
                self.layout.dpath_dicom,
                self.layout.dpath_bids,
            ],
        )

        # run pipeline with Boutiques
        self.launch_boutiques_run(
            participant, session, singularity_command=singularity_command
        )

        # update status
        self.doughnut.set_status(
            participant=participant,
            session=session,
            col=self.doughnut.col_converted,
            status=True,
        )

    def generate_fpath_log(
        self,
        dname_parent: Optional[str | list[str]] = None,
        fname_stem: Optional[str] = None,
    ) -> Path:
        """Generate a log file path."""
        if dname_parent is None:
            dname_parent = get_pipeline_tag(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
                pipeline_step=self.pipeline_step,
            )
        return super().generate_fpath_log(dname_parent, fname_stem)
