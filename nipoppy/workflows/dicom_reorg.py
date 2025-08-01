"""DICOM file organization."""

import os
from pathlib import Path
from typing import Optional

import pydicom

from nipoppy.env import ReturnCode, StrOrPathLike
from nipoppy.tabular.curation_status import update_curation_status_table
from nipoppy.utils import (
    participant_id_to_bids_participant_id,
    session_id_to_bids_session_id,
)
from nipoppy.workflows.base import BaseDatasetWorkflow


def is_derived_dicom(fpath: Path) -> bool:
    """
    Read a DICOM file's header and check if it is a derived file.

    Some BIDS converters (e.g. Heudiconv) do not support derived DICOM files.
    """
    dcm_info = pydicom.dcmread(fpath)
    img_types = dcm_info.ImageType
    return "DERIVED" in img_types


class DicomReorgWorkflow(BaseDatasetWorkflow):
    """Workflow for organizing raw DICOM files."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        copy_files: bool = False,
        check_dicoms: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the DICOM reorganization workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="dicom_reorg",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )
        self.copy_files = copy_files
        self.check_dicoms = check_dicoms

        # the message logged in run_cleanup will depend on
        # the final values for these attributes (updated in run_main)
        self.n_success = 0
        self.n_total = 0

    def get_fpaths_to_reorg(
        self,
        participant_id: str,
        session_id: str,
    ) -> list[Path]:
        """Get file paths to reorganize for a single participant and session."""
        dpath_downloaded = (
            self.layout.dpath_pre_reorg
            / self.dicom_dir_map.get_dicom_dir(
                participant_id=participant_id, session_id=session_id
            )
        )

        # make sure directory exists
        if not dpath_downloaded.exists():
            raise FileNotFoundError(
                f"Raw DICOM directory not found for participant {participant_id}"
                f" session {session_id}: {dpath_downloaded}"
            )

        # crawl through directory tree and get all file paths
        fpaths = []
        for dpath, _, fnames in os.walk(dpath_downloaded):
            fpaths.extend(Path(dpath, fname) for fname in fnames)
        return fpaths

    def apply_fname_mapping(
        self, fpath_source: StrOrPathLike, participant_id: str, session_id: str
    ) -> str:
        """
        Apply a mapping from the original (full) file path to destination file name.

        This method does not change the file name by default, but it can be overridden
        if the file names need to be changed during reorganization (e.g. for easier
        BIDS conversion).
        """
        return Path(fpath_source).name

    def run_single(self, participant_id: str, session_id: str):
        """Reorganize downloaded DICOM files for a single participant and session."""
        # get paths to reorganize
        fpaths_to_reorg = self.get_fpaths_to_reorg(participant_id, session_id)

        dpath_reorganized: Path = (
            self.layout.dpath_post_reorg
            / participant_id_to_bids_participant_id(participant_id)
            / session_id_to_bids_session_id(session_id)
        )
        self.mkdir(dpath_reorganized)

        # do reorg
        for fpath_source in fpaths_to_reorg:
            # check file (though only error out if DICOM cannot be read)
            if self.check_dicoms:
                try:
                    if is_derived_dicom(fpath_source):
                        self.logger.warning(
                            f"Derived DICOM file detected: {fpath_source}"
                        )
                except Exception as exception:
                    raise RuntimeError(
                        f"Error checking DICOM file {fpath_source}: {exception}"
                    )

            # the destination path is under dpath_reorganized
            # resolve the path to avoid issues with symlinks
            fpath_dest = (
                dpath_reorganized
                / self.apply_fname_mapping(
                    fpath_source, participant_id=participant_id, session_id=session_id
                )
            ).resolve()

            # do not overwrite existing files
            if fpath_dest.exists():
                raise FileExistsError(
                    f"Cannot move file {fpath_source} to {fpath_dest}"
                    " because it already exists"
                )

            # either create symlinks or copy original files
            if self.copy_files:
                self.copy(fpath_source, fpath_dest)
            else:
                fpath_source = os.path.relpath(
                    fpath_source.resolve(), fpath_dest.parent
                )
                self.create_symlink(
                    path_source=fpath_source,
                    path_dest=fpath_dest,
                )

        # update curation status
        self.curation_status_table.set_status(
            participant_id=participant_id,
            session_id=session_id,
            col=self.curation_status_table.col_in_post_reorg,
            status=True,
        )

    def get_participants_sessions_to_run(self):
        """Return participant-session pairs to reorganize."""
        participants_sessions_organized = set(
            self.curation_status_table.get_organized_participants_sessions()
        )
        for (
            participant_session
        ) in self.curation_status_table.get_downloaded_participants_sessions():
            if participant_session not in participants_sessions_organized:
                yield participant_session

    def run_setup(self):
        """Update the curation status table in case it is not up-to-date."""
        super().run_setup()
        self.curation_status_table = update_curation_status_table(
            curation_status_table=self.curation_status_table,
            manifest=self.manifest,
            dicom_dir_map=self.dicom_dir_map,
            dpath_downloaded=self.layout.dpath_pre_reorg,
            dpath_organized=self.layout.dpath_post_reorg,
            dpath_bidsified=self.layout.dpath_bids,
            logger=self.logger,
        )

    def run_main(self):
        """Reorganize all downloaded DICOM files."""
        for (
            participant_id,
            session_id,
        ) in self.get_participants_sessions_to_run():
            self.n_total += 1
            try:
                self.run_single(participant_id, session_id)
                self.n_success += 1
            except Exception as exception:
                self.return_code = ReturnCode.PARTIAL_SUCCESS
                self.logger.error(
                    "Error reorganizing DICOM files for participant "
                    f"{participant_id} session {session_id}: {exception}"
                )

    def run_cleanup(self):
        """
        Clean up after main DICOM reorg part is run.

        Specifically:
        - Write updated curation status file
        - Log a summary message
        """
        self.save_tabular_file(
            self.curation_status_table, self.layout.fpath_curation_status
        )

        if self.n_total == 0:
            self.logger.warning(
                "No participant-session pairs to reorganize. Make sure there are no "
                "mistakes in the dataset's manifest or config file, and/or check the "
                f"curation status file at {self.layout.fpath_curation_status}"
            )
        else:
            # change the message depending on how successful the run was
            log_msg = (
                f"Reorganized files for {self.n_success} out of "
                f"{self.n_total} participant-session pairs."
            )
            if self.n_success == 0:
                self.logger.error(log_msg)
            elif self.n_success == self.n_total:
                self.logger.success(log_msg)
            else:
                self.logger.warning(log_msg)

        return super().run_cleanup()
