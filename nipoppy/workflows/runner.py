"""PipelineRunner workflow."""

import subprocess
from functools import cached_property
from pathlib import Path
from tarfile import is_tarfile
from typing import Optional

from boutiques import bosh

from nipoppy.config.boutiques import BoutiquesConfig
from nipoppy.config.container import ContainerConfig, prepare_container
from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import EXT_TAR, StrOrPathLike
from nipoppy.workflows.pipeline import BasePipelineWorkflow


class PipelineRunner(BasePipelineWorkflow):
    """Pipeline runner."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        name: str = "run",
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        keep_workdir: bool = False,
        tar: bool = False,
        simulate: bool = False,
        write_list: Optional[StrOrPathLike] = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        self.simulate = simulate
        self.keep_workdir = keep_workdir
        self.tar = tar
        super().__init__(
            dpath_root=dpath_root,
            name=name,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant_id=participant_id,
            session_id=session_id,
            write_list=write_list,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return super().dpaths_to_check + [
            self.dpath_pipeline_output,
            self.dpath_pipeline_work,
        ]

    def process_container_config(
        self,
        participant_id: str,
        session_id: str,
        bind_paths: Optional[list[StrOrPathLike]] = None,
    ) -> str:
        """Update container config and generate container command."""
        if bind_paths is None:
            bind_paths = []

        # get and process container config
        container_config = self.pipeline_step_config.get_container_config()
        container_config = ContainerConfig(
            **self.process_template_json(
                container_config.model_dump(),
                participant_id=participant_id,
                session_id=session_id,
            )
        )
        self.logger.debug(f"Initial container config: {container_config}")

        # get and process Boutiques config
        boutiques_config = BoutiquesConfig(
            **self.process_template_json(
                self.boutiques_config.model_dump(),
                participant_id=participant_id,
                session_id=session_id,
            )
        )

        # update container config with additional information from Boutiques config
        self.logger.debug(f"Boutiques config: {boutiques_config}")
        if boutiques_config != BoutiquesConfig():
            self.logger.info("Updating container config with config from descriptor")
            container_config.merge(boutiques_config.get_container_config())

        # add bind paths
        for bind_path in bind_paths:
            container_config.add_bind_path(bind_path)

        self.logger.info(f"Using container config: {container_config}")

        container_command = prepare_container(
            container_config,
            subcommand=boutiques_config.CONTAINER_SUBCOMMAND,
            check=True,
            logger=self.logger,
        )

        return container_command

    def launch_boutiques_run(
        self,
        participant_id: str,
        session_id: str,
        objs: Optional[list] = None,
        **kwargs,
    ):
        """Launch a pipeline run using Boutiques."""
        # process and validate the descriptor
        self.logger.info("Processing the JSON descriptor")
        descriptor_str = self.process_template_json(
            self.descriptor,
            participant_id=participant_id,
            session_id=session_id,
            objs=objs,
            **kwargs,
            return_str=True,
        )
        self.logger.debug(f"Descriptor string: {descriptor_str}")
        self.logger.info("Validating the JSON descriptor")
        bosh(["validate", descriptor_str])

        # process and validate the invocation
        self.logger.info("Processing the JSON invocation")
        invocation_str = self.process_template_json(
            self.invocation,
            participant_id=participant_id,
            session_id=session_id,
            objs=objs,
            **kwargs,
            return_str=True,
        )
        self.logger.debug(f"Invocation string: {invocation_str}")
        self.logger.info("Validating the JSON invocation")
        bosh(["invocation", "-i", invocation_str, descriptor_str])

        # run as a subprocess so that stdout/error are captured in the log
        # by default, this will raise an exception if the command fails
        if self.simulate:
            self.logger.info("Simulating pipeline command")
            try:
                self.run_command(
                    ["bosh", "exec", "simulate", "-i", invocation_str, descriptor_str],
                    quiet=True,
                )
            except subprocess.CalledProcessError as exception:
                raise RuntimeError(
                    "Pipeline simulation failed"
                    f" (return code: {exception.returncode})"
                )
        else:
            self.logger.info("Running pipeline command")
            try:
                self.run_command(
                    [
                        "bosh",
                        "exec",
                        "launch",
                        "--stream",
                        descriptor_str,
                        invocation_str,
                    ],
                    quiet=True,
                )
            except subprocess.CalledProcessError as exception:
                raise RuntimeError(
                    "Pipeline did not complete successfully"
                    f" (return code: {exception.returncode})"
                    ". Hint: make sure the shell command above is correct."
                )

        return descriptor_str, invocation_str

    def _check_tar_conditions(self):
        """
        Make sure that conditions for tarring are met if tarring is requested.

        Specifically, check that dpath to tar is specified in the tracker config
        """
        if not self.tar:
            return

        if self.pipeline_step_config.TRACKER_CONFIG_FILE is None:
            raise RuntimeError(
                "Tarring requested but is no tracker config file. "
                "Specify the TRACKER_CONFIG_FILE field for the pipeline step in "
                "the global config file, then make sure the PARTICIPANT_SESSION_DIR "
                "field is specified in the TRACKER_CONFIG_FILE file."
            )
        if self.tracker_config.PARTICIPANT_SESSION_DIR is None:
            raise RuntimeError(
                "Tarring requested but no participant-session directory specified. "
                "The PARTICIPANT_SESSION_DIR field in the tracker config must set "
                "in the tracker config file at "
                f"{self.pipeline_step_config.TRACKER_CONFIG_FILE}"
            )

    def tar_directory(self, dpath: Path) -> Path:
        """Tar a directory and delete it."""
        if not dpath.exists():
            raise RuntimeError(f"Not tarring {dpath} since it does not exist")
        if not dpath.is_dir():
            raise RuntimeError(f"Not tarring {dpath} since it is not a directory")

        tar_flags = "-cvf"
        fpath_tarred = dpath.with_suffix(EXT_TAR)

        self.run_command(
            f"tar {tar_flags} {fpath_tarred} -C {dpath.parent} {dpath.name}"
        )

        # make sure that the tarfile was created successfully before removing
        # original directory
        if fpath_tarred.exists() and is_tarfile(fpath_tarred):
            self.rm(dpath)
        else:
            self.logger.error(f"Failed to tar {dpath} to {fpath_tarred}")

        return fpath_tarred

    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """Generate a list of participant and session IDs to run.

        Specifically, this list will include participants who have BIDS data but
        who have not previously successfully completed the pipeline (according)
        to the bagel file.
        """
        participants_sessions_completed = set(
            self.bagel.get_completed_participants_sessions(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
                pipeline_step=self.pipeline_step,
                participant_id=participant_id,
                session_id=session_id,
            )
        )

        for participant_session in self.doughnut.get_bidsified_participants_sessions(
            participant_id=participant_id, session_id=session_id
        ):
            if participant_session not in participants_sessions_completed:
                yield participant_session

    def run_setup(self):
        """Run pipeline runner setup."""
        to_return = super().run_setup()
        self._check_tar_conditions()

        # fail early if container file is specified but not found
        # otherwise, the exception will be caught in the run_main loop
        # and the program will not actually exit
        try:
            self.fpath_container
        except FileNotFoundError as exception:
            raise exception
        except Exception:
            pass

        return to_return

    def run_single(self, participant_id: str, session_id: str):
        """Run pipeline on a single participant/session."""
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
        container_command = self.process_container_config(
            participant_id=participant_id,
            session_id=session_id,
            bind_paths=[
                self.layout.dpath_bids,
                self.dpath_pipeline_output,
                self.dpath_pipeline_work,
                self.dpath_pipeline_bids_db,
            ],
        )

        # run pipeline with Boutiques
        to_return = self.launch_boutiques_run(
            participant_id, session_id, container_command=container_command
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

        return to_return

    def run_cleanup(self):
        """Run pipeline runner cleanup."""
        if self.n_success == self.n_total:
            if not self.keep_workdir:
                for dpath in [self.dpath_pipeline_bids_db, self.dpath_pipeline_work]:
                    if dpath.exists():
                        self.rm(dpath)
            else:
                self.logger.info("Keeping working / intermediary files.")
        else:
            self.logger.info(
                "Some pipeline segments failed. Keeping working / intermediary files."
            )
        return super().run_cleanup()
