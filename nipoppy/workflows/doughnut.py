"""Workflow for init command."""

from pathlib import Path

from nipoppy.tabular.doughnut import Doughnut, generate_doughnut, update_doughnut
from nipoppy.workflows.workflow import _Workflow


class DoughnutWorkflow(_Workflow):
    """Workflow for creating/updating a dataset's doughnut file."""

    def __init__(self, dpath_root: Path, empty=False, regenerate=False, **kwargs):
        """Initialize the workflow."""
        super().__init__(dpath_root=dpath_root, name="doughnut", **kwargs)

        self.empty = empty
        self.regenerate = regenerate

    def run_main(self):
        """Generate/update the dataset's doughnut file."""
        fpath_doughnut = self.layout.fpath_doughnut
        dpath_downloaded = self.layout.dpath_raw_dicom
        dpath_organized = self.layout.dpath_dicom
        dpath_converted = self.layout.dpath_bids
        empty = self.empty
        logger = self.logger

        if fpath_doughnut.exists() and not self.regenerate:
            old_doughnut = Doughnut.load(fpath_doughnut)
            logger.info(f"Found existing doughnut (shape: {old_doughnut.shape})")
            doughnut = update_doughnut(
                doughnut=old_doughnut,
                manifest=self.manifest,
                dpath_downloaded=dpath_downloaded,
                dpath_organized=dpath_organized,
                dpath_converted=dpath_converted,
                empty=empty,
                logger=logger,
            )

        else:
            if self.regenerate:
                logger.info("Regenerating the entire doughnut")
            else:
                logger.info(f"Did not find existing doughnut at {fpath_doughnut}")
            doughnut = generate_doughnut(
                manifest=self.manifest,
                dpath_downloaded=dpath_downloaded,
                dpath_organized=dpath_organized,
                dpath_converted=dpath_converted,
                empty=empty,
                logger=logger,
            )

        logger.info(f"New/updated doughnut (shape: {doughnut.shape})")
        if not self.dry_run:
            fpath_doughnut_backup = doughnut.save_with_backup(fpath_doughnut)
            if fpath_doughnut_backup is not None:
                logger.info(
                    f"Saved doughnut to {fpath_doughnut} (-> {fpath_doughnut_backup})"
                )
            else:
                logger.info(f"No changes to doughnut at {fpath_doughnut}")
        else:
            logger.info(
                f"Not writing doughnut to {fpath_doughnut} since this is a dry run"
            )
