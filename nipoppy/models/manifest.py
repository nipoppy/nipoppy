"""Class for the dataset manifest."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from nipoppy.models.tabular import _Tabular, _TabularModel


class Manifest(_Tabular):
    """A dataset's manifest."""

    # column names
    col_participant_id = "participant_id"
    col_visit = "visit"
    col_session = "session"
    col_datatype = "datatype"

    # for code autocompletion
    # should match above column names
    participant_id: pd.Series
    visit: pd.Series
    session: pd.Series
    datatype: pd.Series

    class ManifestModel(_TabularModel):
        """Model for the manifest."""

        participant_id: str
        visit: str
        session: Optional[str] = None
        datatype: list[str] = []

        @classmethod
        def _validate_fields(cls, input: dict):
            if Manifest.col_datatype in input:
                try:
                    input[Manifest.col_datatype] = pd.eval(input[Manifest.col_datatype])
                except Exception:
                    raise ValueError(
                        f"Invalid datatype: {input[Manifest.col_datatype]}"
                        ". Must be a list or left empty"
                    )
            return input

    # set the model
    model = ManifestModel
