"""Workflow for status command."""

from pathlib import Path
from typing import Optional

import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table

from nipoppy.env import StrOrPathLike
from nipoppy.layout import DEFAULT_LAYOUT_INFO
from nipoppy.tabular.bagel import STATUS_SUCCESS
from nipoppy.workflows.base import BaseWorkflow


class StatusWorkflow(BaseWorkflow):
    """Workflow for status command."""

    def __init__(
        self,
        dpath_root: Path,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="status",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logging=True,
        )
        self.col_pipeline = "pipeline"

    def run_main(self):
        """Check the status of the dataset and report.

        1) Number of participants in manifest per BIDS datatype,
        2) Doughnut information if available,
        3) Bagel information if available
        """
        # load global_config to get the dataset name
        dataset_name = self.config.DATASET_NAME
        expected_sessions = self.config.SESSION_IDS
        expected_visits = self.config.VISIT_IDS

        self.logger.info(f"Dataset name: {dataset_name}")
        self.logger.info(f"\tExpected sessions: {sorted(expected_sessions)}")
        self.logger.info(f"\tExpected visits: {sorted(expected_visits)}")

        status_df = pd.DataFrame()
        status_df = self._check_manifest(status_df)
        status_df, doughnut_cols = self._check_doughnut(status_df)
        status_df, bagel_cols = self._check_bagel(status_df)

        status_df = status_df.fillna(0).astype(int)

        # define the status columns and rewards columns
        status_col_dict = {
            "manifest": "in_manifest",
            "doughnut": doughnut_cols,
            "bids": "in_bids",  # also part of doughnut cols
            "bagel": bagel_cols,
        }

        # reorder the columns
        status_df = status_df[
            [status_col_dict["manifest"]] + doughnut_cols + bagel_cols
        ]

        self.logger.debug(status_df)

        self._df_to_table(status_df, status_col_dict)

        return status_df

    def _check_manifest(self, status_df: pd.DataFrame) -> pd.DataFrame:
        """Check the manifest file."""
        nipoppy_checkpoint = "in_manifest"
        self.logger.info("Manifest status")

        manifest = self.manifest

        # Get the number of participants in the manifest
        participant_ids = manifest[manifest.col_participant_id].unique()

        # Get the number of sessions in the manifest
        visit_ids = sorted(manifest[manifest.col_visit_id].unique())

        # filter participants with imaging data
        imaging_manifest = manifest.get_imaging_subset()
        imaging_participant_ids = imaging_manifest[
            imaging_manifest.col_participant_id
        ].unique()

        # Get the number of imaging sessions in the manifest
        session_ids = sorted(imaging_manifest[manifest.col_session_id].unique())

        self.logger.info(
            f"\tNumber of participants (imaging and non-imaging): "
            f"{len(participant_ids)}"
        )
        self.logger.info(
            f"\tVisits (imaging and non-imaging) (n={len(visit_ids)}): {visit_ids}"
        )
        self.logger.info(
            f"\tNumber of participants with imaging data: "
            f"{len(imaging_participant_ids)}"
        )
        self.logger.info(f"\tImaging sessions (n={len(session_ids)}): {session_ids}")

        manifest_status_df = imaging_manifest.groupby(
            [imaging_manifest.col_session_id]
        ).count()[[imaging_manifest.col_participant_id]]
        manifest_status_df.columns = [nipoppy_checkpoint]

        self.logger.debug(f"bagel_status_df:\n{manifest_status_df}")
        status_df = pd.concat([status_df, manifest_status_df], axis=1)
        return status_df

    def _check_doughnut(self, status_df: pd.DataFrame) -> pd.DataFrame:
        """Check the doughnut file (if exists)."""
        nipoppy_checkpoint = "in_doughnut"

        self.logger.debug(f"Status at nipoppy_checkpoint: {nipoppy_checkpoint}")
        doughnut = self.doughnut

        if doughnut.empty:
            self.logger.warning("No doughnut file found.")
            return status_df, []

        doughnut_cols = [
            doughnut.col_in_pre_reorg,
            doughnut.col_in_post_reorg,
            doughnut.col_in_bids,
        ]

        # Get the number of participants in the doughnut
        participant_ids = doughnut[doughnut.col_participant_id].unique()
        session_ids = doughnut[doughnut.col_session_id].unique()

        self.logger.debug(
            f"\tNumber of participants in doughnut: {len(participant_ids)}"
        )
        self.logger.debug(f"\tAvailable sessions (n={len(session_ids)}): {session_ids}")

        doughnut_status_df = doughnut.groupby([doughnut.col_session_id]).sum()[
            doughnut_cols
        ]

        self.logger.debug(f"doughnut_status_df: {doughnut_status_df}")
        status_df = pd.concat([status_df, doughnut_status_df], axis=1)
        return status_df, doughnut_cols

    def _check_bagel(self, status_df: pd.DataFrame) -> pd.DataFrame:
        """Check the imaging bagel file (if exists)."""
        nipoppy_checkpoint = "in_imaging_bagel"

        self.logger.debug(f"Status at nipoppy_checkpoint: {nipoppy_checkpoint}")
        bagel = self.bagel

        if bagel.empty:
            self.logger.warning(
                "No imaging bagel file found. Run 'nipoppy track' to"
                " generate an imaging bagel file"
            )
            return status_df, []

        # Get the number of participants in the bagel
        participant_ids = bagel[bagel.col_participant_id].unique()
        session_ids = bagel[bagel.col_session_id].unique()
        pipelines = bagel[bagel.col_pipeline_name].unique()

        self.logger.debug(f"\tNumber of participants in bagel: {len(participant_ids)}")
        self.logger.debug(f"\tAvailable visits (n={len(session_ids)}): {session_ids}")
        self.logger.debug(f"\tAvailable pipelines (n={len(pipelines)}): {pipelines}")

        # Check if at least successful run exists
        if bagel[bagel[bagel.col_status] == STATUS_SUCCESS].empty:
            self.logger.warning(
                "The imaging bagel file exists, but no successful run was found in"
                f" the imaging bagel file for pipeline(s): {pipelines}."
                " If you have run a pipeline followed by 'nipoppy track', it is"
                " likely that your pipeline output does not meet the criteria in the"
                f" '{DEFAULT_LAYOUT_INFO.dpath_pipelines}/<PIPELINE_NAME>-"
                "<PIPELINE_VERSION>/tracker_config.json' file."
                " Please check the tracker configuration and re-run 'nipoppy track'"
                " to generate an imaging bagel file with at least one successful run."
            )
            return status_df, []

        bagel[self.col_pipeline] = (
            bagel[bagel.col_pipeline_name]
            + "\n"
            + bagel[bagel.col_pipeline_version]
            + "\n"
            + bagel[bagel.col_pipeline_step]
        )

        bagel_pipeline_df = bagel[
            [
                bagel.col_participant_id,
                bagel.col_session_id,
                self.col_pipeline,
                bagel.col_status,
            ]
        ]
        bagel_pipeline_df = bagel_pipeline_df[
            bagel_pipeline_df[bagel.col_status] == STATUS_SUCCESS
        ]

        bagel_pipeline_df = bagel_pipeline_df.pivot(
            index=[bagel.col_participant_id, bagel.col_session_id],
            columns=self.col_pipeline,
            values=bagel.col_status,
        )

        bagel_status_df = bagel_pipeline_df.groupby([bagel.col_session_id]).count()

        self.logger.debug(f"bagel_status_df: {bagel_status_df}")

        status_df = pd.concat([status_df, bagel_status_df], axis=1)

        bagel_cols = list(status_df.columns[status_df.columns.str.contains("\n")])
        return status_df, bagel_cols

    def _df_to_table(self, status_df: pd.DataFrame, status_col_dict: dict):
        """Convert a pandas.DataFrame obj into a rich.Table obj."""
        df = status_df.copy().reset_index()
        df = df.sort_values(by=self.manifest.col_session_id)

        console = Console()

        # Define the colors for the columns
        column_colors = {
            "session_id": None,
            "in_manifest": "chartreuse4",
            "in_pre_reorg": "cyan",
            "in_post_reorg": "cornflower_blue",
            "in_bids": "medium_purple3",
            "in_imaging_bagel": [
                "orchid",
                "deep_pink4",
                "hot_pink3",
                "dark_orange",
            ],
        }

        # Initiate a Table instance
        title = "Participant counts by session at each Nipoppy checkpoint"

        table = Table(title=title, collapse_padding=False)

        bagel_cols = status_col_dict["bagel"]
        n_non_proc_cols = 0
        for i_col, column in enumerate(df.columns):
            if column not in (bagel_cols):
                col_color = column_colors[column]
                n_non_proc_cols += 1
            else:
                proc_colors = column_colors["in_imaging_bagel"]
                col_color = proc_colors[(i_col - n_non_proc_cols) % len(proc_colors)]

            column_header = column

            table.add_column(
                str(column_header),
                style=col_color,
                header_style=col_color,
                justify="center",
                vertical="top",  # vertical alignment doesn't work :(
            )

        for value_list in df.values.tolist():
            row = [str(x) for x in value_list]
            table.add_row(*row)

        # Update the style of the table
        table.box = box.MINIMAL_DOUBLE_HEAD  # SIMPLE_HEAD
        console.print(table)
