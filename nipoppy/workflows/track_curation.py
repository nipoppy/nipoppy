"""Workflow for init command."""

from pathlib import Path
from typing import Optional

from nipoppy.env import StrOrPathLike
from nipoppy.logger import get_logger
from nipoppy.tabular.curation_status import (
    CurationStatusTable,
    generate_curation_status_table,
    update_curation_status_table,
)
from nipoppy.workflows.base import BaseDatasetWorkflow, _save_tabular_file

logger = get_logger()


class TrackCurationWorkflow(BaseDatasetWorkflow):
    """Workflow for creating/updating a dataset's curation status file."""

    def __init__(
        self,
        dpath_root: Path,
        empty: bool = False,
        force: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="nipoppy_track_curation",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

        self.empty = empty
        self.force = force

    def run_main(self):
        """Generate/update the dataset's curation status file."""
        fpath_table = self.study.layout.fpath_curation_status
        dpath_downloaded = self.study.layout.dpath_pre_reorg
        dpath_organized = self.study.layout.dpath_post_reorg
        dpath_bidsified = self.study.layout.dpath_bids
        empty = self.empty

        if fpath_table.exists() and not self.force:
            old_table = CurationStatusTable.load(fpath_table)
            logger.info(
                f"Found existing curation status file (shape: {old_table.shape})"
            )
            table = update_curation_status_table(
                curation_status_table=old_table,
                manifest=self.study.manifest,
                dicom_dir_map=self.dicom_dir_map,
                dpath_downloaded=dpath_downloaded,
                dpath_organized=dpath_organized,
                dpath_bidsified=dpath_bidsified,
                empty=empty,
            )

        else:
            if self.force:
                logger.info("Regenerating the entire curation status file")
            else:
                logger.info(
                    f"Did not find existing curation status file at {fpath_table}"
                )
            table = generate_curation_status_table(
                manifest=self.study.manifest,
                dicom_dir_map=self.dicom_dir_map,
                dpath_downloaded=dpath_downloaded,
                dpath_organized=dpath_organized,
                dpath_bidsified=dpath_bidsified,
                empty=empty,
            )

        logger.info(f"New/updated curation status table shape: {table.shape}")
        _save_tabular_file(table, fpath_table, dry_run=self.dry_run)

    def run_cleanup(self):
        """Log a success message."""
        logger.success(
            "Successfully generated/updated the dataset's curation status file"
        )
        return super().run_cleanup()
