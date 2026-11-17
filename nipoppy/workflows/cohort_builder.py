"""Build a cohort of participant-session pairs from the dataset tabular files."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable

COL_IN_MANIFEST = "in_manifest"
COL_PIPELINES = "pipelines"


@dataclass(frozen=True)
class CohortItem:
    """All the known information about a participant-session pair."""

    participant_id: str
    session_id: str
    in_manifest: bool
    in_prereorg: bool
    in_postreorg: bool
    in_bids: bool
    # One dict per processing status record (pipeline name, version, step, status...)
    pipelines: list[dict[str, str]]


class CohortBuilder:
    """Build the parent table with all the information."""

    index_cols = [Manifest.col_participant_id, Manifest.col_session_id]

    def __init__(
        self,
        manifest: Manifest,
        curation_status: CurationStatusTable,
        processing_status: ProcessingStatusTable,
    ):
        self._manifest = manifest
        self._curation_status = curation_status
        self._processing_status = processing_status

    def build_table(self) -> pd.DataFrame:
        """Merge the manifest, curation status and processing status.

        Returns
        -------
        pd.DataFrame
            One row per manifest record (participant-visit), plus one row for each
            participant-session pair found only in the curation or processing status.
            Columns are all the manifest columns, ``in_manifest``,
            ``participant_dicom_dir`` and the curation status columns, and
            ``pipelines``: a list with one dict per processing status record.
        """
        # 1. every manifest record (the manifest is keyed by participant and visit,
        #    and session_id can be empty, so do not drop duplicates or columns)
        table = pd.DataFrame(self._manifest).copy()
        table[COL_IN_MANIFEST] = True

        # 2. curation status columns
        curation_cols = [
            CurationStatusTable.col_participant_dicom_dir,
            *CurationStatusTable.status_cols,
        ]
        curation = pd.DataFrame(self._curation_status)[self.index_cols + curation_cols]
        table = table.merge(curation, on=self.index_cols, how="outer")

        # 3. all the processing status records of each participant-session pair
        processing = pd.DataFrame(self._processing_status)
        if processing.empty:
            table[COL_PIPELINES] = None
        else:
            pipelines = (
                processing.groupby(self.index_cols)[
                    [col for col in processing.columns if col not in self.index_cols]
                ]
                .apply(lambda records: records.to_dict(orient="records"))
                .rename(COL_PIPELINES)
                .reset_index()
            )
            table = table.merge(pipelines, on=self.index_cols, how="outer")

        # pairs missing from a table have empty values: turn them into False and []
        table[COL_IN_MANIFEST] = table[COL_IN_MANIFEST].eq(True)
        table[CurationStatusTable.status_cols] = table[
            CurationStatusTable.status_cols
        ].eq(True)
        table[COL_PIPELINES] = table[COL_PIPELINES].apply(
            lambda records: records if isinstance(records, list) else []
        )
        return table

    def get_participant_session_pairs(self) -> Iterable[CohortItem]:
        """Yield one CohortItem per table row that has a session.

        Manifest records without a session (no imaging data) are skipped.
        """
        table = self.build_table()
        for _, row in table.iterrows():
            if pd.isna(row[Manifest.col_session_id]):
                continue
            yield CohortItem(
                participant_id=row[Manifest.col_participant_id],
                session_id=row[Manifest.col_session_id],
                in_manifest=row[COL_IN_MANIFEST],
                in_prereorg=row[CurationStatusTable.col_in_pre_reorg],
                in_postreorg=row[CurationStatusTable.col_in_post_reorg],
                in_bids=row[CurationStatusTable.col_in_bids],
                pipelines=row[COL_PIPELINES],
            )
