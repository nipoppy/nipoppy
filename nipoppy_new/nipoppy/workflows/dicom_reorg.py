"""DICOM file organization."""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from nipoppy.workflows.base import BaseWorkflow


class DicomReorgWorkflow(BaseWorkflow):
    """Workflow for organizing raw DICOM files."""

    def __init__(
        self,
        dpath_root: Path | str,
        copy_files: bool = True,
        fpath_layout: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
    ):
        """Initialize the DICOM reorganization workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="dicom_reorg",
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.copy_files = copy_files

    def run_single(self, participant: str, session: str):
        """Reorganize downloaded DICOM files for a single participant and session."""
        # find directory with files to reorganize
        dpath_downloaded: Path = self.layout.dpath_raw_dicom / session / participant
        if not dpath_downloaded.exists():
            raise FileNotFoundError(
                f"Raw DICOM directory not found for participant {participant}"
                f" session {session}: {dpath_downloaded}"
            )

        # do reorg
        dpath_reorganized: Path = self.layout.dpath_sourcedata / participant / session
        dpath_reorganized.mkdir(parents=True, exist_ok=True)
        for dpath, _, fnames in os.walk(dpath_downloaded):
            for fname in fnames:
                fpath_source = Path(dpath, fname)
                fpath_dest = dpath_reorganized / fname

                # do not overwrite existing files
                if fpath_dest.exists():
                    raise FileExistsError(
                        f"Cannot move file {fpath_source} to {fpath_dest}"
                        " because it already exists"
                    )

                # either create symlinks or copy original files
                if self.copy_files:
                    shutil.copyfile(fpath_source, fpath_dest)
                else:
                    fpath_source = os.path.relpath(fpath_source, fpath_dest.parent)
                    os.symlink(fpath_source, fpath_dest)

                # update doughnut entry
                self.doughnut.set_status(
                    participant=participant,
                    session=session,
                    col=self.doughnut.col_organized,
                    status=True,
                )

    def run_main(self):
        """Reorganize all downloaded DICOM files."""
        for (
            participant,
            session,
        ) in self.doughnut.get_downloaded_participants_sessions():
            try:
                self.run_single(participant, session)
            except Exception as exception:
                self.logger.error(
                    "Error reorganizing DICOM files"
                    f" for participant {participant} session {session}: {exception}"
                )
