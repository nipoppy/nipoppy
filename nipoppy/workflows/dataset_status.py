"""Workflow for status command."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table

from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.tabular.bagel import STATUS_SUCCESS, Bagel
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.tabular.manifest import Manifest
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
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="status",
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.save_status_to_disk = save_status_to_disk  # TODO maybe
        self.status_df = pd.DataFrame()

    def run_main(self):
        """Check the status of the dataset and report.

        1) Number of participants in manifest per BIDS datatype,
        2) Doughnut information if available,
        3) Bagel information if available
        """
        self.logger.info("Checking the status of the dataset.")
        self.check_manifest()
        self.check_doughnut()
        self.check_bagel()

        self.logger.debug(self.status_df)

        self.df_to_table()

        # TODO
        # save the status to a file (probably needs a schema)
        # check if previous status file exists
        # if so, compare the two and report the differences

    def check_manifest(self):
        """Check the manifest file."""
        nipoppy_checkpoint = "in_manifest"
        self.logger.info(f"***Status at nipoppy_checkpoint: {nipoppy_checkpoint}***")

        manifest = Manifest.load(self.layout.fpath_manifest).validate()

        # Get the number of participants in the manifest
        participant_ids = manifest[manifest.col_participant_id].unique()

        # Get the number of sessions in the manifest
        visit_ids = manifest[manifest.col_visit_id].unique()

        # filter participants with imaging data
        imaging_manifest = manifest.get_imaging_subset()
        imaging_participant_ids = imaging_manifest[
            imaging_manifest.col_participant_id
        ].unique()

        # Get the number of imaging sessions in the manifest
        session_ids = imaging_manifest[manifest.col_session_id].unique()

        self.logger.info(
            f"Number of participants (imaging and non-imaging): {len(participant_ids)}"
        )
        self.logger.info(
            f"Available  visits (imaging and non-imaging) (n={len(visit_ids)}): "
            f"{visit_ids}"
        )
        self.logger.info(
            f"Number of participants with imaging data: {len(imaging_participant_ids)}"
        )
        self.logger.info(
            f"Number of imaging sessions (n={len(session_ids)}): {session_ids}"
        )

        manifest_status_df = imaging_manifest.groupby(
            [imaging_manifest.col_session_id]
        ).count()[[imaging_manifest.col_participant_id]]
        manifest_status_df.columns = [nipoppy_checkpoint]

        self.logger.debug(f"bagel_status_df: {manifest_status_df}")
        self.status_df = pd.concat([self.status_df, manifest_status_df], axis=1)

    def check_doughnut(self):
        """Check the doughnut file (if exists)."""
        nipoppy_checkpoint = "in_doughnut"

        self.logger.info(f"***Status at nipoppy_checkpoint: {nipoppy_checkpoint}***")

        if not self.layout.fpath_doughnut.exists():
            self.logger.info(f"No doughnut file found at {self.layout.fpath_doughnut}.")
            return

        doughnut = Doughnut.load(self.layout.fpath_doughnut)

        # Get the number of participants in the doughnut
        participant_ids = doughnut[doughnut.col_participant_id].unique()
        session_ids = doughnut[doughnut.col_session_id].unique()

        self.logger.info(f"Number of participants in doughnut: {len(participant_ids)}")
        self.logger.info(f"Available visits (n={len(session_ids)}): {session_ids}")

        doughnut_status_df = doughnut.groupby([doughnut.col_session_id]).sum()[
            [
                doughnut.col_in_pre_reorg,
                doughnut.col_in_post_reorg,
                doughnut.col_in_bids,
            ]
        ]

        self.logger.debug(f"doughnut_status_df: {doughnut_status_df}")
        self.status_df = pd.concat([self.status_df, doughnut_status_df], axis=1)

    def check_bagel(self):
        """Check the imaging bagel file (if exists)."""
        nipoppy_checkpoint = "in_imaging_bagel"

        self.logger.info(f"***Status at nipoppy_checkpoint: {nipoppy_checkpoint}***")

        if not self.layout.fpath_imaging_bagel.exists():
            self.logger.info(
                f"No bagel file found at {self.layout.fpath_imaging_bagel}."
            )
            return

        bagel = Bagel.load(self.layout.fpath_imaging_bagel)

        # Get the number of participants in the doughnut
        participant_ids = bagel[bagel.col_participant_id].unique()
        session_ids = bagel[bagel.col_session_id].unique()
        pipelines = bagel[bagel.col_pipeline_name].unique()

        self.logger.info(f"Number of participants in bagel: {len(participant_ids)}")
        self.logger.info(f"Available visits (n={len(session_ids)}): {session_ids}")
        self.logger.info(f"Available pipelines (n={len(pipelines)}): {pipelines}")

        bagel["pipeline"] = (
            bagel[bagel.col_pipeline_name]
            + "_"
            + bagel[bagel.col_pipeline_version]
            + "_"
            + bagel[bagel.col_pipeline_step]
        )

        bagel_pipeline_df = bagel[
            [
                bagel.col_participant_id,
                bagel.col_session_id,
                "pipeline",
                bagel.col_status,
            ]
        ]
        bagel_pipeline_df = bagel_pipeline_df[
            bagel_pipeline_df[bagel.col_status] == STATUS_SUCCESS
        ]

        bagel_pipeline_df = bagel_pipeline_df.pivot(
            index=[bagel.col_participant_id, bagel.col_session_id],
            columns="pipeline",
            values=bagel.col_status,
        )

        bagel_status_df = bagel_pipeline_df.groupby([bagel.col_session_id]).count()

        self.logger.debug(f"bagel_status_df: {bagel_status_df}")

        self.status_df = pd.concat([self.status_df, bagel_status_df], axis=1)

    def df_to_table(self):
        """Convert a pandas.DataFrame obj into a rich.Table obj."""
        console = Console()

        # Initiate a Table instance
        title = "Participant counts at each nipoppy checkpoint"
        table = Table(show_header=True, header_style="bold red", title=title)
        df = self.status_df.copy()
        df = df.fillna(0).astype(int).reset_index()

        for column in df.columns:
            table.add_column(str(column))

        for value_list in df.values.tolist():
            row = []
            row += [str(x) for x in value_list]
            table.add_row(*row)

        # Update the style
        table.row_styles = ["none", "dim"]
        table.box = box.SIMPLE_HEAD
        console.print(table)

    def run_cleanup(self):
        """Log a success message."""
        self.logger.info(
            f"[{LogColor.SUCCESS}]Successfully reported the current "
            f"status of a dataset at {self.dpath_root}![/]"
        )
        return super().run_cleanup()
