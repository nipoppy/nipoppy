"""PipelineRunner workflow."""

from functools import cached_property
from pathlib import Path
from tarfile import is_tarfile
from typing import Optional

from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import EXT_TAR, PROGRAM_NAME, StrOrPathLike
from nipoppy.exceptions import ConfigError, FileOperationError
from nipoppy.logger import get_logger
from nipoppy.utils import fileops
from nipoppy.workflows.base import run_command
from nipoppy.workflows.runner import Runner

logger = get_logger()


class ProcessingRunner(Runner):
    """Pipeline runner."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        name: str = "process",
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        use_subcohort: Optional[StrOrPathLike] = None,
        simulate: bool = False,
        keep_workdir: bool = False,
        tar: bool = False,
        write_subcohort: Optional[StrOrPathLike] = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
        hpc: Optional[str] = None,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name=name,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant_id=participant_id,
            session_id=session_id,
            use_subcohort=use_subcohort,
            write_subcohort=write_subcohort,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            hpc=hpc,
            simulate=simulate,
            keep_workdir=keep_workdir,
        )
        self.tar = tar

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return [
            self.dpath_pipeline_output,
            self.dpath_pipeline_work,
        ]

    def _check_tar_conditions(self):
        """
        Make sure that conditions for tarring are met if tarring is requested.

        Specifically, check that dpath to tar is specified in the tracker config
        """
        if not self.tar:
            return

        if self.pipeline_step_config.TRACKER_CONFIG_FILE is None:
            raise ConfigError(
                "Tarring requested but there is no tracker config file. "
                "Specify the TRACKER_CONFIG_FILE field for the pipeline step in "
                "the global config file, then make sure the PARTICIPANT_SESSION_DIR "
                "field is specified in the TRACKER_CONFIG_FILE file."
            )
        if self.tracker_config.PARTICIPANT_SESSION_DIR is None:
            raise ConfigError(
                "Tarring requested but no participant-session directory specified. "
                "The PARTICIPANT_SESSION_DIR field in the tracker config must set "
                "in the tracker config file at "
                f"{self.pipeline_step_config.TRACKER_CONFIG_FILE}"
            )

    def tar_directory(self, dpath: StrOrPathLike) -> Path:
        """Tar a directory and delete it."""
        dpath = Path(dpath)
        if not dpath.exists():
            raise FileOperationError(f"Not tarring {dpath} since it does not exist")
        if not dpath.is_dir():
            raise FileOperationError(f"Not tarring {dpath} since it is not a directory")

        tar_flags = "-cvf"
        fpath_tarred = dpath.with_suffix(EXT_TAR)

        run_command(
            f"tar {tar_flags} {fpath_tarred} -C {dpath.parent} {dpath.name}",
            dry_run=self.dry_run,
        )

        # make sure that the tarfile was created successfully before removing
        # original directory
        if fpath_tarred.exists() and is_tarfile(fpath_tarred):
            fileops.rm(dpath, dry_run=self.dry_run)
        else:
            logger.error(f"Failed to tar {dpath} to {fpath_tarred}")

        return fpath_tarred

    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """Generate a list of participant and session IDs to run.

        Specifically, this list will include participants who have BIDS data but
        who have not previously successfully completed the pipeline (according)
        to the processing status file.
        """
        participants_sessions_completed = set(
            self.processing_status_table.get_completed_participants_sessions(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
                pipeline_step=self.pipeline_step,
                participant_id=participant_id,
                session_id=session_id,
            )
        )

        for (
            participant_session
        ) in self.curation_status_table.get_bidsified_participants_sessions(
            participant_id=participant_id, session_id=session_id
        ):
            if participant_session not in participants_sessions_completed:
                yield participant_session

    def _generate_cli_command_for_hpc(
        self, participant_id=None, session_id=None
    ) -> list[str]:
        """
        Generate the CLI command to be run on the HPC cluster for a participant/session.

        Skip the --simulate, --hpc, --write-list and --dry-run options.
        """
        command = [
            PROGRAM_NAME,
            "process",
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
        if self.tar:
            command.append("--tar")
        if self.fpath_layout:
            command.extend(["--layout", self.fpath_layout])
        if self.verbose:
            command.append("--verbose")
        return [str(component) for component in command]

    def run_setup(self):
        """Run pipeline runner setup."""
        to_return = super().run_setup()
        self._check_tar_conditions()

        # fail early if container file is specified but not found
        # otherwise, the exception will be caught in the run_main loop
        # and the program will not actually exit
        try:
            self.fpath_container
        except FileOperationError:
            raise
        except Exception:
            pass

        return to_return

    def run_single(self, participant_id: str, session_id: str):
        """Run pipeline on a single participant/session."""
        logger.info(f"Running for participant {participant_id}, session {session_id}")

        # Access the GENERATE_PYBIDS_DATABASE field
        generate_bids_db = self.pipeline_step_config.GENERATE_PYBIDS_DATABASE

        # Conditionally set up PyBIDS database
        if generate_bids_db:
            self.set_up_bids_db(
                dpath_pybids_db=self.dpath_pipeline_bids_db,
                participant_id=participant_id,
                session_id=session_id,
            )

        # get container command
        launch_boutiques_run_kwargs = {}
        if self.study.config.CONTAINER_CONFIG.COMMAND is not None:
            container_command, container_handler = self.process_container_config(
                participant_id=participant_id,
                session_id=session_id,
                bind_paths=[
                    self.study.layout.dpath_bids,
                    self.dpath_pipeline_output,
                    self.dpath_pipeline_work,
                    self.dpath_pipeline_bids_db,
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

        if self.tar and not self.simulate:
            tracker_config = TrackerConfig(
                **self.process_template_json(
                    self.tracker_config.model_dump(mode="json"),
                    participant_id=participant_id,
                    session_id=session_id,
                )
            )
            self.tar_directory(
                self.dpath_pipeline_output / tracker_config.PARTICIPANT_SESSION_DIR
            )

        return invocation_and_descriptor

    def run_cleanup(self):
        """Run pipeline runner cleanup."""
        if self.n_success == self.n_total:
            if not self.keep_workdir:
                for dpath in [self.dpath_pipeline_bids_db, self.dpath_pipeline_work]:
                    if dpath.exists():
                        fileops.rm(dpath, dry_run=self.dry_run)
            else:
                logger.info("Keeping working / intermediary files.")
        else:
            logger.info(
                "Some pipeline segments failed. Keeping working / intermediary files."
            )
        return super().run_cleanup()
