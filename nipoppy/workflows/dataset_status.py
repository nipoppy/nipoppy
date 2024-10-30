"""Workflow for init command."""

import logging
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
import pandas as pd

from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    LogColor,
    StrOrPathLike,
)
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.workflows.base import BaseWorkflow


class StatusWorkflow(BaseWorkflow):
    """Workflow for status command."""

    def __init__(
        self,
        dpath_root: Path,        
        fpath_layout: Optional[StrOrPathLike] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
        save_status_to_disk: bool = False,
        status_df: pd.DataFrame = None,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="init",
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.fname_readme = "README.md"
        self.save_status_to_disk = save_status_to_disk
        self.status_df = pd.DataFrame()

    def run_main(self):
        """Check the status of the dataset and report
        1) Number of participants in manifest per BIDS datatype,
        2) Doughnut information if available,
        3) Bagel information if available
        """
        self.logger.info("Checking the status of the dataset.")
        self.check_manifest()
        self.check_doughnut()
        self.check_bagel()

        # self.logger.info(self.status_df)

    def check_manifest(self):
        """Check the manifest file."""
        
        nipoppy_artifact = "manifest"

        manifest = Manifest.load(self.layout.fpath_manifest).validate()

        # Get the number of participants in the manifest
        participant_ids = manifest[manifest.col_participant_id].unique()

        # Get the number of sessions in the manifest
        visit_ids = manifest[manifest.col_visit_id].unique()

        # filter participants with imaging data
        imaging_manifest = manifest.get_imaging_subset()
        imaging_participant_ids = imaging_manifest[imaging_manifest.col_participant_id].unique()

        # Get the number of imaging sessions in the manifest
        session_ids = imaging_manifest[manifest.col_session_id].unique()

        self.logger.info(f"Number of participants (imaging and non-imaging): {len(participant_ids)}")
        self.logger.info(f"Available visits (n={len(visit_ids)}): {visit_ids}")
        self.logger.info(f"Number of participants with imaging data: {len(imaging_participant_ids)}")
        self.logger.info(f"Number of sessions (n={len(session_ids)}): {session_ids}")

        manifest_status_df = imaging_manifest.groupby(
            [imaging_manifest.col_session_id]
            ).size().reset_index(name='counts')        

        manifest_status_df["nipoppy_artefact"]  = nipoppy_artifact

        self.logger.info(manifest_status_df)

        self.status_df = pd.concat([self.status_df, manifest_status_df])


    def check_doughnut(self):
        """Check the doughnut file (if exists)."""
        # TODO
        nipoppy_artifact = "doughnut"
        doughnut = Doughnut.load(self.layout.fpath_doughnut)

        # Get the number of participants in the doughnut
        participant_ids = doughnut[doughnut.col_participant_id].unique()
        sesion_ids = doughnut[doughnut.col_session_id].unique()

        self.logger.info(f"Number of participants in doughnut: {len(participant_ids)}")
        self.logger.info(f"Available visits (n={len(sesion_ids)}): {sesion_ids}")

        doughnut_status_df = doughnut.groupby(
            [
                doughnut.col_session_id, 
                doughnut.col_in_raw_imaging, 
                doughnut.col_in_sourcedata, 
                doughnut.col_in_bids
                ]
            ).size().reset_index(name='counts')
        
        doughnut_status_df["nipoppy_artefact"]  = nipoppy_artifact

        self.logger.info(doughnut_status_df)
        
        self.status_df = pd.concat([self.status_df, doughnut_status_df])
        

    def check_bagel(self):
        # TODO
        pass

    def run_cleanup(self):
        """Log a success message."""
        self.logger.info(
            f"[{LogColor.SUCCESS}]Successfully reported the current status of a dataset "
            f"at {self.dpath_root}![/]"
        )
        return super().run_cleanup()
