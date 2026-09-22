"""Workflow for init command."""

from pathlib import Path

from nipoppy.env import StrOrPathLike
from nipoppy.logger import get_logger
from nipoppy.tabular.curation_status import generate_curation_status_table
from nipoppy.workflows.base import BaseDatasetWorkflow

logger = get_logger()


class TrackCurationWorkflow(BaseDatasetWorkflow):
    """Workflow for creating/updating a dataset's curation status file."""

    def __init__(
        self,
        dpath_root: Path,
        fpath_layout: StrOrPathLike | None = None,
        verbose: bool = False,
        dry_run: bool = False,
        regenerate: bool | None = None,  # deprecated
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="track_curation",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )
        self.regenerate = regenerate  # not used but needed for __repr__ to work

    def run_main(self):
        """Generate/update the dataset's curation status file."""
        fpath_table = self.study.layout.fpath_curation_status
        dpath_downloaded = self.study.layout.dpath_pre_reorg
        dpath_organized = self.study.layout.dpath_post_reorg
        dpath_bidsified = self.study.layout.dpath_bids

        table = generate_curation_status_table(
            manifest=self.study.manifest,
            dicom_dir_map=self.dicom_dir_map,
            dpath_downloaded=dpath_downloaded,
            dpath_organized=dpath_organized,
            dpath_bidsified=dpath_bidsified,
        )

        logger.info(f"Curation status table shape: {table.shape}")
        table.save_with_backup(fpath_table, dry_run=self.dry_run)

        logger.success(
            "Successfully generated/updated the dataset's curation status file"
        )
