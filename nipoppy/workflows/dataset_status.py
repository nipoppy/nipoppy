"""Workflow for status command."""

import pandas as pd
from rich import box
from rich.table import Table

from nipoppy.console import CONSOLE_STDOUT
from nipoppy.env import StrOrPathLike
from nipoppy.layout import DEFAULT_LAYOUT_INFO
from nipoppy.logger import get_logger
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import (
    STATUS_SUCCESS,
    ProcessingStatusTable,
)
from nipoppy.workflows.base import BaseDatasetWorkflow

logger = get_logger()

COL_CHECKPOINT = "checkpoint"
CHECKPOINT_MANIFEST = "in_manifest"

INDEX_COLS = CurationStatusTable.index_cols

LONG_STATUS_COLUMNS = [*INDEX_COLS, Manifest.col_datatype, COL_CHECKPOINT]


def _empty_status_df() -> pd.DataFrame:
    """Create an empty long-form status table with the canonical schema."""
    return pd.DataFrame(columns=LONG_STATUS_COLUMNS)


def _get_manifest_datatypes(imaging_manifest: pd.DataFrame) -> pd.DataFrame:
    """Get the datatypes of each imaging participant-session pair in the manifest.

    (participant_id, session_id) is assumed to be unique (see #1234).
    """
    columns = [*INDEX_COLS, Manifest.col_datatype]
    if imaging_manifest.empty:
        return pd.DataFrame(columns=columns)

    manifest_datatypes = imaging_manifest[columns].reset_index(drop=True)
    manifest_datatypes[Manifest.col_datatype] = manifest_datatypes[
        Manifest.col_datatype
    ].apply(lambda value: value if isinstance(value, list) else [])
    return manifest_datatypes


def _attach_manifest_datatypes(
    status_df: pd.DataFrame, manifest_datatypes: pd.DataFrame
) -> pd.DataFrame:
    """Attach manifest datatypes and discard status-only records."""
    if status_df.empty or manifest_datatypes.empty:
        return _empty_status_df()

    return status_df.drop(columns=Manifest.col_datatype, errors="ignore").merge(
        manifest_datatypes,
        on=INDEX_COLS,
        how="inner",
        validate="many_to_one",
    )[LONG_STATUS_COLUMNS]


def _curation_status_to_long(
    table: CurationStatusTable, manifest_datatypes: pd.DataFrame
) -> pd.DataFrame:
    """Normalize completed curation checkpoints to the long-form schema."""
    if table.empty:
        logger.warning("No curation status file found.")
        return _empty_status_df()

    status_df = table[[*INDEX_COLS, *CurationStatusTable.status_cols]].melt(
        id_vars=INDEX_COLS,
        value_vars=CurationStatusTable.status_cols,
        var_name=COL_CHECKPOINT,
        value_name="complete",
    )
    status_df = status_df.loc[status_df.pop("complete")]
    return _attach_manifest_datatypes(status_df, manifest_datatypes)


def _processing_status_to_long(
    table: ProcessingStatusTable, manifest_datatypes: pd.DataFrame
) -> pd.DataFrame:
    """Normalize successful processing checkpoints to the long-form schema."""
    if table.empty:
        logger.warning(
            "No imaging processing status file found. Run "
            "'nipoppy track-processing' to generate a processing status file"
        )
        return _empty_status_df()

    successful = table.loc[
        table[ProcessingStatusTable.col_status] == STATUS_SUCCESS
    ].copy()
    if successful.empty:
        pipeline_names = sorted(table[ProcessingStatusTable.col_pipeline_name].unique())
        logger.warning(
            "The processing status file exists, but no successful run was found in"
            " the imaging processing status file for pipeline(s): "
            f"{pipeline_names}."
            " If you have run a pipeline followed by 'nipoppy track-processing', it"
            " is likely that your pipeline output does not meet the criteria in the"
            f" '{DEFAULT_LAYOUT_INFO.dpath_pipelines}/<PIPELINE_NAME>-"
            "<PIPELINE_VERSION>/tracker_config.json' file."
            " Please check the tracker configuration and re-run "
            "'nipoppy track-processing' to generate a processing status file with "
            "at least one successful run."
        )
        return _empty_status_df()

    successful[COL_CHECKPOINT] = (
        successful[ProcessingStatusTable.col_pipeline_name]
        + "\n"
        + successful[ProcessingStatusTable.col_pipeline_version]
        + "\n"
        + successful[ProcessingStatusTable.col_pipeline_step]
    )
    return _attach_manifest_datatypes(successful, manifest_datatypes)


def _filter_status_df(
    status_df: pd.DataFrame, *, datatypes: set[str] | None = None
) -> pd.DataFrame:
    """Filter long-form records by exact manifest datatype membership."""
    if datatypes is None:
        return status_df.copy()

    return status_df.loc[
        status_df[Manifest.col_datatype].apply(datatypes.issubset)
    ].copy()


def _get_session_ids(status_df: pd.DataFrame) -> list[str]:
    """Get deterministic session ordering from the selected status records."""
    return sorted(status_df[Manifest.col_session_id].unique())


def _count_by_session(
    status_df: pd.DataFrame,
    session_ids: list[str],
    checkpoint_cols: list[str],
) -> pd.DataFrame:
    """Count completed checkpoints for each session."""
    status_counts_df = (
        status_df.groupby([Manifest.col_session_id, COL_CHECKPOINT], sort=False)
        .size()
        .unstack(fill_value=0)
        .reindex(
            index=session_ids,
            columns=checkpoint_cols,
            fill_value=0,
        )
        .astype(int)
    )

    status_counts_df.index.name = Manifest.col_session_id
    status_counts_df.columns.name = None
    return status_counts_df


class StatusWorkflow(BaseDatasetWorkflow):
    """Workflow for status command."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        fpath_layout: StrOrPathLike | None = None,
        verbose: bool = False,
        dry_run: bool = False,
        datatype: tuple[str, ...] | str | None = None,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="status",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logfile=True,
        )
        self.datatype = datatype
        if isinstance(datatype, str):
            datatype = (datatype,)
        if datatype is None:
            datatype = ()
        datatypes = set(datatype)
        self.datatypes: set[str] | None = datatypes or None

    def run_main(self) -> pd.DataFrame | None:
        """Build, filter, and summarize dataset status records by session.

        Returns
        -------
        pd.DataFrame or None
            Status dataframe with completed checkpoint counts by session, or
            None if the manifest has no imaging data or no record matches the
            requested datatypes.
        """
        status_df = self._build_status_df()
        if status_df.empty:
            logger.warning(
                "No imaging participant-session pairs found in the manifest."
            )
            return None

        status_df = _filter_status_df(status_df, datatypes=self.datatypes)
        if status_df.empty:
            logger.warning(
                f"No imaging manifest rows matched datatype: {self.datatypes}."
            )
            return None

        curation_cols = CurationStatusTable.status_cols
        processing_cols = sorted(
            set(status_df[COL_CHECKPOINT])
            - {CHECKPOINT_MANIFEST, *CurationStatusTable.status_cols}
        )
        checkpoint_cols = [CHECKPOINT_MANIFEST, *curation_cols, *processing_cols]
        session_ids = _get_session_ids(status_df)

        self._log_dataset_summary(status_df, session_ids)

        status_counts_df = _count_by_session(
            status_df,
            session_ids=session_ids,
            checkpoint_cols=checkpoint_cols,
        )

        if status_counts_df[CurationStatusTable.col_in_bids].equals(
            status_counts_df[CHECKPOINT_MANIFEST]
        ):
            logger.info(
                "BIDSification completed: hiding counts for pre- and post-reorg stages."
            )
            status_counts_df = status_counts_df.drop(
                [
                    CurationStatusTable.col_in_pre_reorg,
                    CurationStatusTable.col_in_post_reorg,
                ],
                axis=1,
            )

        self._print_table(status_counts_df, processing_cols)

        return status_counts_df

    def _build_status_df(self) -> pd.DataFrame:
        """Build one long-form table from manifest and completed status records."""
        imaging_manifest = pd.DataFrame(self.study.manifest.get_imaging_subset()).copy()
        manifest_datatypes = _get_manifest_datatypes(imaging_manifest)
        manifest_long = manifest_datatypes.copy()
        manifest_long[COL_CHECKPOINT] = CHECKPOINT_MANIFEST

        status_df = pd.concat(
            [
                manifest_long,
                _curation_status_to_long(
                    self.curation_status_table, manifest_datatypes
                ),
                _processing_status_to_long(
                    self.processing_status_table, manifest_datatypes
                ),
            ],
            ignore_index=True,
        )
        status_df = status_df[LONG_STATUS_COLUMNS]
        logger.debug(f"Long-form status table:\n{status_df}")
        return status_df

    def _log_dataset_summary(self, status_df: pd.DataFrame, session_ids: list[str]):
        """Log manifest summary information for the selected dataset rows."""
        manifest = self.study.manifest
        participant_ids = manifest[Manifest.col_participant_id].unique()
        visit_ids = sorted(manifest[Manifest.col_visit_id].unique())

        imaging_participant_ids = status_df[Manifest.col_participant_id].unique()
        logger.info(
            "Dataset summary (based on the manifest file):"
            f"\tNumber of participants (imaging and non-imaging): "
            f"{len(participant_ids)}"
            f"\n\tVisits (imaging and non-imaging) (n={len(visit_ids)}): {visit_ids}"
            f"\n\tNumber of participants with imaging data: "
            f"{len(imaging_participant_ids)}"
            f"\n\tImaging sessions (n={len(session_ids)}): {session_ids}"
        )

    def _print_table(
        self,
        status_df: pd.DataFrame,
        processing_cols: list[str],
    ):
        """Convert a pandas.DataFrame obj into a rich.Table obj."""
        df = status_df.copy().reset_index()
        df = df.sort_values(by=Manifest.col_session_id)

        # Define the colors for the columns
        column_colors = {
            Manifest.col_session_id: None,
            CHECKPOINT_MANIFEST: "chartreuse4",
            CurationStatusTable.col_in_pre_reorg: "cyan",
            CurationStatusTable.col_in_post_reorg: "cornflower_blue",
            CurationStatusTable.col_in_bids: "medium_purple3",
            "processing": [
                "orchid",
                "deep_pink4",
                "hot_pink3",
                "dark_orange",
            ],
        }

        # Initiate a Table instance
        title = "Participant counts by session at each Nipoppy checkpoint"

        table = Table(title=title, box=box.MINIMAL_DOUBLE_HEAD, collapse_padding=False)

        n_non_proc_cols = 0
        for i_col, column in enumerate(df.columns):
            if column not in processing_cols:
                col_color = column_colors[column]
                n_non_proc_cols += 1
            else:
                proc_colors = column_colors["processing"]
                col_color = proc_colors[(i_col - n_non_proc_cols) % len(proc_colors)]

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

        CONSOLE_STDOUT.print(table)
