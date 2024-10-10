"""Workflow for convert command."""

from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path
from typing import Optional

from nipoppy.config.pipeline import ExtractionPipelineConfig
from nipoppy.config.pipeline_step import ExtractionPipelineStepConfig
from nipoppy.env import StrOrPathLike
from nipoppy.workflows.runner import PipelineRunner


class ExtractionRunner(PipelineRunner):
    """Convert data to BIDS."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        simulate: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant_id=participant_id,
            session_id=session_id,
            simulate=simulate,
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.name = "nipoppy_extract"

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return [self.dpath_pipeline_idps]

    @cached_property
    def _pipeline_configs(self) -> list[ExtractionPipelineConfig]:
        return self.config.EXTRACTION_PIPELINES

    @cached_property
    def pipeline_config(self) -> ExtractionPipelineConfig:
        """Get the user config for the BIDS conversion pipeline."""
        return super().pipeline_config

    @cached_property
    def pipeline_step_config(self) -> ExtractionPipelineStepConfig:
        """Get the config for the relevant step of the BIDS conversion pipeline."""
        return super().pipeline_step_config

    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """Return participant-session pairs to run the pipeline on."""
        for participant_session in self.bagel.get_completed_participants_sessions(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            participant_id=participant_id,
            session_id=session_id,
        ):
            yield participant_session

    def run_single(self, participant_id: str, session_id: str):
        """Run extractor on a single participant/session."""
        # get container command
        container_command = self.process_container_config(
            participant_id=participant_id,
            session_id=session_id,
            bind_paths=[
                self.layout.dpath_sourcedata,
                self.layout.dpath_bids,
            ],
        )

        # run pipeline with Boutiques
        invocation_and_descriptor = self.launch_boutiques_run(
            participant_id, session_id, container_command=container_command
        )

        return invocation_and_descriptor
