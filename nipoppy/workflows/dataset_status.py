"""Workflow for status command."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table

from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.tabular.bagel import STATUS_SUCCESS
from nipoppy.workflows.base import BaseWorkflow


class StatusWorkflow(BaseWorkflow):
    """Workflow for status command."""

    def __init__(
        self,
        dpath_root: Path,
        fpath_layout: Optional[StrOrPathLike] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
        # TODO in future release
        # save_status_to_disk: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="status",
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.col_pipeline = "pipeline"

        # TODO in future release
        # self.save_status_to_disk = save_status_to_disk

    def run_main(self):
        """Check the status of the dataset and report.

        1) Number of participants in manifest per BIDS datatype,
        2) Doughnut information if available,
        3) Bagel information if available
        """
        self.logger.info("Checking the status of the dataset.")

        # load global_config to get the dataset name
        # dataset_name = self.config.DATASET_NAME
        # self.logger.info(f"Dataset name: {dataset_name}")

        status_df = pd.DataFrame()

        status_df = self._check_manifest(status_df)
        status_df = self._check_doughnut(status_df)
        status_df = self._check_bagel(status_df)
        status_df, legend_dict = self._add_rewards(status_df)

        self.logger.debug(status_df)

        self._df_to_table(status_df, legend_dict)

        # TODO in future release
        # save the status to a file (probably needs a schema)
        # check if previous status file exists
        # if so, compare the two and report the differences

        return status_df

    def _check_manifest(self, status_df: pd.DataFrame) -> pd.DataFrame:
        """Check the manifest file."""
        nipoppy_checkpoint = "in_manifest"
        self.logger.info(f"Status at nipoppy_checkpoint: {nipoppy_checkpoint}")

        manifest = self.manifest

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
            f"\tNumber of participants (imaging and non-imaging): "
            f"{len(participant_ids)}"
        )
        self.logger.info(
            f"\tAvailable  visits (imaging and non-imaging) (n={len(visit_ids)}): "
            f"{visit_ids}"
        )
        self.logger.info(
            f"\tNumber of participants with imaging data: "
            f"{len(imaging_participant_ids)}"
        )
        self.logger.info(
            f"\tNumber of imaging sessions (n={len(session_ids)}): " f"{session_ids}"
        )

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

        self.logger.info(f"Status at nipoppy_checkpoint: {nipoppy_checkpoint}")

        try:
            doughnut = self.doughnut
        except FileNotFoundError:
            self.logger.warning(
                f"No doughnut file found at {self.layout.fpath_doughnut}."
            )
            return

        # Get the number of participants in the doughnut
        participant_ids = doughnut[doughnut.col_participant_id].unique()
        session_ids = doughnut[doughnut.col_session_id].unique()

        self.logger.info(
            f"\tNumber of participants in doughnut: {len(participant_ids)}"
        )
        self.logger.info(f"\tAvailable visits (n={len(session_ids)}): {session_ids}")

        doughnut_status_df = doughnut.groupby([doughnut.col_session_id]).sum()[
            [
                doughnut.col_in_pre_reorg,
                doughnut.col_in_post_reorg,
                doughnut.col_in_bids,
            ]
        ]

        self.logger.debug(f"doughnut_status_df: {doughnut_status_df}")
        status_df = pd.concat([status_df, doughnut_status_df], axis=1)
        return status_df

    def _check_bagel(self, status_df: pd.DataFrame) -> pd.DataFrame:
        """Check the imaging bagel file (if exists)."""
        nipoppy_checkpoint = "in_imaging_bagel"

        self.logger.info(f"Status at nipoppy_checkpoint: {nipoppy_checkpoint}")

        try:
            bagel = self.bagel
        except FileNotFoundError:
            self.logger.warning(
                f"No bagel file found at {self.layout.fpath_imaging_bagel}."
            )
            return

        # Get the number of participants in the bagel
        participant_ids = bagel[bagel.col_participant_id].unique()
        session_ids = bagel[bagel.col_session_id].unique()
        pipelines = bagel[bagel.col_pipeline_name].unique()

        self.logger.info(f"\tNumber of participants in bagel: {len(participant_ids)}")
        self.logger.info(f"\tAvailable visits (n={len(session_ids)}): {session_ids}")
        self.logger.info(f"\tAvailable pipelines (n={len(pipelines)}): {pipelines}")

        bagel[self.col_pipeline] = (
            bagel[bagel.col_pipeline_name]
            + "\n"
            + ""
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
        return status_df

    def _add_rewards(self, status_df: pd.DataFrame) -> pd.DataFrame:
        """Add rewards column to the status DataFrame."""
        status_df = status_df.fillna(0).astype(int).reset_index()
        status_df = status_df.sort_values(by=self.manifest.col_session_id)

        # generate positive reinforcement emojis
        clipboard = "📋"

        sad_cat_emoji = "😿"
        broom_emoji = "🧹"
        doughnut_emoji = "🍩"
        sparkles_emoji = "✨"
        rocket_emoji = "🚀"
        bagel_emoji = "🥯"
        party_popper_emoji = "🎉"
        confetti_emoji = "🎊"

        # based on quantity
        high_throughput = 100
        bento_box_emoji = "🍱"  # 100 subjects in BIDS
        mate_emoji = "🧉"  # 100 subjects processed

        # secret rewards based on quantity
        # shaved_ice_emoji = "🍧"
        # sushi_emoji = "🍣"

        # secret rewards based on update time and date
        # night_owl_emoji = "🦉"
        # slow_sloth_emoji = "🦥"
        # quick_tiger_emoji = "🐅"

        # emoji legend
        legend_dict = {
            sad_cat_emoji: "No available data are curated or processed",
            broom_emoji: "Data clean-up (i.e. BIDSification) has started!",
            doughnut_emoji: "Curation in progress... Doughnut is made!",
            sparkles_emoji: "BIDSification is complete! Tidiness sparks joy!",
            rocket_emoji: "Data processing has launched successfully!",
            bagel_emoji: "Data processing in progress... Bagels are baking!",
            party_popper_emoji: "At least 1 pipeline processing is complete!",
            confetti_emoji: "All data are curated and processed. Time to celebrate!",
        }

        doughnut_cols = ["in_pre_reorg", "in_post_reorg", "in_bids"]
        bagel_cols = [col for col in status_df.columns if "\n" in col]
        non_session_cols = ["in_manifest"] + doughnut_cols + bagel_cols
        for row_obj in status_df.iterrows():
            row = row_obj[1]

            row_stickers = []
            if row["in_manifest"] > 0:
                if (row[doughnut_cols] == 0).all() & (row[bagel_cols] == 0).all():
                    row_stickers.append(sad_cat_emoji)
                else:
                    row_stickers.append(clipboard)

            # curation tasks
            if (row[doughnut_cols] > 0).all():
                row_stickers.append(doughnut_emoji)
            if row["in_bids"] == row["in_manifest"]:
                row_stickers.append(sparkles_emoji)
            elif (row["in_bids"] > 0) & (row["in_bids"] < row["in_manifest"]):
                row_stickers.append(broom_emoji)

            if row["in_bids"] > high_throughput:  # hard to test
                row_stickers.append(bento_box_emoji)

            # processing tasks
            if (row[bagel_cols] > 0).all():
                row_stickers.append(bagel_emoji)

            # check if processing is complete for all participants and pipelines
            if (row[non_session_cols] > 0).all():
                row_vals = row[non_session_cols].values
                all_equal = all([x == row_vals[0] for x in row_vals])
                if all_equal:
                    row_stickers.append(confetti_emoji)

            # Cannot nest this in prior if statement because
            # some pipeline count might be zero
            if (not all_equal) & (row[bagel_cols] == row["in_manifest"]).any():
                row_stickers.append(party_popper_emoji)
            elif (row[bagel_cols] > 0).any():
                row_stickers.append(rocket_emoji)

            if (row[bagel_cols] > high_throughput).any():  # hard to test
                row_stickers.append(mate_emoji)

            status_df.loc[row_obj[0], "rewards"] = " ".join(row_stickers)

        return status_df, legend_dict

    def _df_to_table(self, status_df: pd.DataFrame, legend_dict: dict):
        """Convert a pandas.DataFrame obj into a rich.Table obj."""
        df = status_df.copy()
        console = Console()

        crossed_fingers_emoji = "🤞"
        column_colors = [
            "cyan",
            "magenta",
            "yellow",
            "green",
            "deep_sky_blue3",
            "deep_pink2",
            "rosy_brown",
        ]

        # Initiate a Table instance
        title = (
            "Participant counts by session at each Nipoppy checkpoint"
            + f" {crossed_fingers_emoji} {crossed_fingers_emoji}"
        )

        table = Table(title=title, collapse_padding=False)

        # check if number of colors match the number of columns
        n_colors = len(column_colors)
        n_columns = len(df.columns)
        if n_colors < n_columns:  # cycle through the colors
            column_colors = (
                column_colors * (n_columns // n_colors + 1)
                + column_colors[: n_columns % n_colors]
            )

        for column, col_color in zip(df.columns, column_colors):
            table.add_column(
                str(column),
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
        table.caption = "Legend: " + f"{legend_dict}"
        console.print(table)

    def run_cleanup(self):
        """Log a success message."""
        self.logger.info(
            f"[{LogColor.SUCCESS}]Successfully reported the current "
            f"status of a dataset at {self.dpath_root}![/]"
        )
        return super().run_cleanup()
