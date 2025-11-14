"""Workflow for convert command."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Optional

from nipoppy.config.pipeline import (
    ExtractionPipelineConfig,
    PipelineInfo,
    ProcessingPipelineConfig,
)
from nipoppy.config.pipeline_step import ExtractionPipelineStepConfig
from nipoppy.env import PROGRAM_NAME, PipelineTypeEnum, StrOrPathLike
from nipoppy.workflows.runner import Runner


class ExtractionRunner(Runner):
    """Extract imaging-derived phenotypes (IDPs) from processed data."""

    _pipeline_type = PipelineTypeEnum.EXTRACTION

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        use_subcohort: Optional[StrOrPathLike] = None,
        simulate: bool = False,
        keep_workdir: bool = False,
        hpc: Optional[str] = None,
        write_subcohort: Optional[StrOrPathLike] = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name="extract",
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant_id=participant_id,
            session_id=session_id,
            use_subcohort=use_subcohort,
            simulate=simulate,
            keep_workdir=keep_workdir,
            hpc=hpc,
            write_subcohort=write_subcohort,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return [self.dpath_pipeline_work, self.dpath_pipeline_idp]

    @cached_property
    def pipeline_config(self) -> ExtractionPipelineConfig:
        """Get the user config object for the extraction pipeline."""
        return super().pipeline_config

    # for type annotation only
    @cached_property
    def pipeline_step_config(self) -> ExtractionPipelineStepConfig:
        """Get the config for the relevant step of the extraction pipeline."""
        return super().pipeline_step_config

    @cached_property
    def proc_pipeline_info(self) -> PipelineInfo:
        """Get info about the first processing pipeline associated with extractor.

        Also make sure that the processing pipeline configuration exists.
        """
        proc_pipeline_info = self.pipeline_config.PROC_DEPENDENCIES[0]

        self._get_pipeline_config(
            self.layout.get_dpath_pipeline_bundle(
                PipelineTypeEnum.PROCESSING,
                proc_pipeline_info.NAME,
                proc_pipeline_info.VERSION,
            ),
            pipeline_name=proc_pipeline_info.NAME,
            pipeline_version=proc_pipeline_info.VERSION,
            pipeline_class=ProcessingPipelineConfig,
        ).get_step_config(step_name=proc_pipeline_info.STEP)

        return proc_pipeline_info

    @cached_property
    def dpath_pipeline(self) -> Path:
        """Get the path to the derivatives directory associated with the extractor."""
        return self.layout.get_dpath_pipeline(
            pipeline_name=self.proc_pipeline_info.NAME,
            pipeline_version=self.proc_pipeline_info.VERSION,
        )

    @cached_property
    def dpath_pipeline_output(self) -> Path:
        """Return the path to the pipeline's output directory."""
        return self.layout.get_dpath_pipeline_output(
            pipeline_name=self.proc_pipeline_info.NAME,
            pipeline_version=self.proc_pipeline_info.VERSION,
        )

    @cached_property
    def dpath_pipeline_idp(self) -> Path:
        """Return the path to the pipeline's IDP directory."""
        return self.layout.get_dpath_pipeline_idp(
            pipeline_name=self.proc_pipeline_info.NAME,
            pipeline_version=self.proc_pipeline_info.VERSION,
        )

    def _generate_cli_command_for_hpc(
        self, participant_id=None, session_id=None
    ) -> list[str]:
        """
        Generate the CLI command to be run on the HPC cluster for a participant/session.

        Skip the --simulate, --hpc, --write-list and --dry-run options.
        """
        command = [
            PROGRAM_NAME,
            "extract",
            "--dataset",
            self.dpath_root,
            "--pipeline",
            self.pipeline_name,
        ]
        if self.pipeline_version is not None:
            command.extend(["--pipeline-version", self.pipeline_version])
        if self.pipeline_step is not None:
            command.extend(["--pipeline-step", self.pipeline_step])
        if participant_id is not None:
            command.extend(["--participant-id", participant_id])
        if session_id is not None:
            command.extend(["--session-id", session_id])
        if self.keep_workdir:
            command.append("--keep-workdir")
        if self.fpath_layout:
            command.extend(["--layout", self.fpath_layout])
        if self.verbose:
            command.append("--verbose")
        return [str(component) for component in command]

    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """Return participant-session pairs to run the pipeline on."""
        # get the intersection of participants/sessions that have completed
        # all the processing pipelines that the extraction pipeline depends on
        participants_sessions = None
        for proc_pipeline_info in self.pipeline_config.PROC_DEPENDENCIES:
            to_update = set(
                self.processing_status_table.get_completed_participants_sessions(
                    pipeline_name=proc_pipeline_info.NAME,
                    pipeline_version=proc_pipeline_info.VERSION,
                    pipeline_step=proc_pipeline_info.STEP,
                    participant_id=participant_id,
                    session_id=session_id,
                )
            )
            if participants_sessions is None:
                participants_sessions = to_update
            else:
                participants_sessions = participants_sessions & to_update

        for participant_session in sorted(list(participants_sessions)):
            yield participant_session

    def run_single(self, participant_id: str, session_id: str):
        """Run extractor on a single participant/session."""
        # get container command
        launch_boutiques_run_kwargs = {}
        if self.config.CONTAINER_CONFIG.COMMAND is not None:
            container_command, container_handler = self.process_container_config(
                participant_id=participant_id,
                session_id=session_id,
                bind_paths=[
                    self.dpath_pipeline_idp,
                    self.dpath_pipeline_output,
                ],
            )
            launch_boutiques_run_kwargs["container_command"] = container_command
            launch_boutiques_run_kwargs["container_handler"] = container_handler

        # run pipeline with Boutiques
        invocation_and_descriptor = self.launch_boutiques_run(
            participant_id,
            session_id,
            **launch_boutiques_run_kwargs,
        )

        return invocation_and_descriptor
