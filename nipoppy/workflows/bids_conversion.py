"""Workflow for convert command."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Optional

from nipoppy.config.pipeline import BIDSificationPipelineConfig
from nipoppy.config.pipeline_step import BidsPipelineStepConfig
from nipoppy.env import PROGRAM_NAME, PipelineTypeEnum, StrOrPathLike
from nipoppy.workflows.runner import Runner


class BIDSificationRunner(Runner):
    """Convert data to BIDS."""

    _pipeline_type = PipelineTypeEnum.BIDSIFICATION

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
            name="bids_conversion",
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
    def dpath_pipeline(self):
        """Not available."""
        raise RuntimeError(
            f'"dpath_pipeline" attribute is not available for {type(self)}'
        )

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return [self.dpath_pipeline_work]

    @cached_property
    def pipeline_config(self) -> BIDSificationPipelineConfig:
        """Get the user config object for the BIDS pipeline."""
        return super().pipeline_config

    @cached_property
    def pipeline_step_config(self) -> BidsPipelineStepConfig:
        """Get the config for the relevant step of the BIDS conversion pipeline."""
        return super().pipeline_step_config

    def _generate_cli_command_for_hpc(
        self, participant_id=None, session_id=None
    ) -> list[str]:
        """
        Generate the CLI command to be run on the HPC cluster for a participant/session.

        Skip the --simulate, --hpc, --write-list and --dry-run options.
        """
        command = [
            PROGRAM_NAME,
            "bidsify",
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
        participants_sessions_bidsified = set(
            self.curation_status_table.get_bidsified_participants_sessions(
                participant_id=participant_id, session_id=session_id
            )
        )
        for (
            participant_session
        ) in self.curation_status_table.get_organized_participants_sessions(
            participant_id=participant_id, session_id=session_id
        ):
            if participant_session not in participants_sessions_bidsified:
                yield participant_session

    def run_single(self, participant_id: str, session_id: str):
        """Run BIDS conversion on a single participant/session."""
        # get container command
        launch_boutiques_run_kwargs = {}
        if self.config.CONTAINER_CONFIG.COMMAND is not None:
            container_command, container_handler = self.process_container_config(
                participant_id=participant_id,
                session_id=session_id,
                bind_paths=[
                    self.study.layout.dpath_post_reorg,
                    self.study.layout.dpath_bids,
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

        # update status
        if self.pipeline_step_config.UPDATE_STATUS:
            self.curation_status_table.set_status(
                participant_id=participant_id,
                session_id=session_id,
                col=self.curation_status_table.col_in_bids,
                status=True,
            )

        return invocation_and_descriptor

    def run_cleanup(self, **kwargs):
        """
        Clean up after main BIDS conversion part is run.

        Specifically:

        - Write updated curation status file
        """
        if self.pipeline_step_config.UPDATE_STATUS and not self.simulate:
            self.save_tabular_file(
                self.curation_status_table, self.study.layout.fpath_curation_status
            )
        return super().run_cleanup(**kwargs)
