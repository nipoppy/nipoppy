"""Workflow for init command."""

from pathlib import Path
from typing import Optional

from nipoppy.env import StrOrPathLike
from nipoppy.tabular.curation_status import (
    CurationStatusTable,
    generate_curation_status_table,
    update_curation_status_table,
)
from nipoppy.workflows.base import BaseDatasetWorkflow


class TrackCurationWorkflow(BaseDatasetWorkflow):
    """Workflow for creating/updating a dataset's curation status file."""

    def __init__(
        self,
        dpath_root: Path,
        empty: bool = False,
        regenerate: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="track_curation",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

        self.empty = empty
        self.regenerate = regenerate

    def run_main(self):
        """Generate/update the dataset's curation status file."""
        fpath_table = self.layout.fpath_curation_status
        dpath_downloaded = self.layout.dpath_pre_reorg
        dpath_organized = self.layout.dpath_post_reorg
        dpath_bidsified = self.layout.dpath_bids
        empty = self.empty
        logger = self.logger

        if fpath_table.exists() and not self.regenerate:
            old_table = CurationStatusTable.load(fpath_table)
            logger.info(
                f"Found existing curation status file (shape: {old_table.shape})"
            )
            table = update_curation_status_table(
                curation_status_table=old_table,
                manifest=self.manifest,
                dicom_dir_map=self.dicom_dir_map,
                dpath_downloaded=dpath_downloaded,
                dpath_organized=dpath_organized,
                dpath_bidsified=dpath_bidsified,
                empty=empty,
                logger=logger,
            )

        else:
            if self.regenerate:
                logger.info("Regenerating the entire curation status file")
            else:
                logger.info(
                    f"Did not find existing curation status file at {fpath_table}"
                )
            table = generate_curation_status_table(
                manifest=self.manifest,
                dicom_dir_map=self.dicom_dir_map,
                dpath_downloaded=dpath_downloaded,
                dpath_organized=dpath_organized,
                dpath_bidsified=dpath_bidsified,
                empty=empty,
                logger=logger,
            )

        logger.info(f"New/updated curation status table shape: {table.shape}")
        self.save_tabular_file(table, fpath_table)

    def run_cleanup(self):
        """Log a success message."""
        self.logger.success(
            "Successfully generated/updated the dataset's curation status file!"
        )
        return super().run_cleanup()
