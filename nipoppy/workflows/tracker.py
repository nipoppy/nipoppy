"""PipelineTracker workflow."""

import tarfile
from pathlib import Path
from typing import Optional

from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import EXT_TAR, StrOrPathLike
from nipoppy.tabular.bagel import Bagel
from nipoppy.workflows.pipeline import BasePipelineWorkflow


class PipelineTracker(BasePipelineWorkflow):
    """Pipeline tracker."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name="track",
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant_id=participant_id,
            session_id=session_id,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

    def run_setup(self):
        """Load/initialize the bagel file."""
        rv = super().run_setup()
        if self.layout.fpath_imaging_bagel.exists():
            try:
                self.bagel = Bagel.load(self.layout.fpath_imaging_bagel)
                self.logger.info(
                    f"Found existing bagel with shape {self.bagel.shape}"
                    f" at {self.layout.fpath_imaging_bagel}"
                )
            except ValueError as exception:
                if "Error when validating the bagel" in str(exception):
                    self.logger.warning(
                        "Failed to load existing bagel at "
                        f"{self.layout.fpath_imaging_bagel}. Generating a new bagel."
                        f"\nOriginal error:\n{exception}"
                    )
                    self.bagel = Bagel()
        else:
            self.bagel = Bagel()
            self.logger.info("Initialized empty bagel")
        return rv

    def check_status(
        self,
        relative_paths: StrOrPathLike,
        relative_dpath_tarred: Optional[StrOrPathLike] = None,
    ):
        """Check the processing status based on a list of expected paths."""
        # collect list of paths in tarball if it exists
        paths_tarred = []
        if relative_dpath_tarred is not None:
            fpath_tarball = (
                self.dpath_pipeline_output / f"{relative_dpath_tarred}{EXT_TAR}"
            )
            if fpath_tarball.exists():
                with tarfile.open(fpath_tarball) as tarball:
                    paths_tarred = tarball.getnames()

        for relative_path in relative_paths:
            relative_path = Path(relative_path)
            self.logger.debug(
                f"Checking path {self.dpath_pipeline_output / relative_path}"
            )

            matches_glob = list(self.dpath_pipeline_output.glob(str(relative_path)))
            self.logger.debug(f"Matches: {matches_glob}")

            # also check tarball paths if applicable/needed
            if (not matches_glob) and (relative_dpath_tarred is not None):
                # NOTE
                # The behaviour of Path.match() is not exactly the same as glob
                # but it should be good enough for now. What we really need is
                # Path.full_match(), but that was only introduced in Python 3.13
                matches_tarred = [
                    path_tarred
                    for path_tarred in paths_tarred
                    if Path(path_tarred).match(
                        str(
                            Path(relative_path).relative_to(
                                Path(relative_dpath_tarred).parent
                            )
                        ),
                    )
                ]
                self.logger.debug(f"Matches in tarball: {matches_tarred}")
            else:
                matches_tarred = []

            if not (matches_glob or matches_tarred):
                return Bagel.status_fail

        return Bagel.status_success

    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """Get participant-session pairs with BIDS data to run the tracker on."""
        return self.doughnut.get_bidsified_participants_sessions(
            participant_id=participant_id, session_id=session_id
        )

    def run_single(self, participant_id: str, session_id: str):
        """Run tracker on a single participant/session."""
        # replace template strings in the tracker config
        tracker_config = TrackerConfig(
            **self.process_template_json(
                self.tracker_config.model_dump(mode="json"),
                participant_id=participant_id,
                session_id=session_id,
            )
        )

        # check status and update bagel
        status = self.check_status(
            tracker_config.PATHS, tracker_config.PARTICIPANT_SESSION_DIR
        )
        self.logger.debug(f"Status: {status}")
        self.bagel = self.bagel.add_or_update_records(
            {
                Bagel.col_participant_id: participant_id,
                Bagel.col_session_id: session_id,
                Bagel.col_pipeline_name: self.pipeline_name,
                Bagel.col_pipeline_version: self.pipeline_version,
                Bagel.col_pipeline_step: self.pipeline_step,
                Bagel.col_status: status,
            }
        )
        return status

    def run_cleanup(self):
        """Save the bagel file."""
        self.logger.info(f"New/updated bagel shape: {self.bagel.shape}")
        self.save_tabular_file(self.bagel, self.layout.fpath_imaging_bagel)
        return super().run_cleanup()
