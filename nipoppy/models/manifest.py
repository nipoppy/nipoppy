"""Model for the tabular manifest file."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd
from pydantic import BaseModel, model_validator


class Manifest(pd.DataFrame):
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

    class _Model(BaseModel):
        participant_id: str
        visit: str
        session: Optional[str] = None
        datatype: list[str] = []

        @model_validator(mode="before")
        @classmethod
        def _validate_input(cls, input: Any):
            if isinstance(input, dict):
                # remove empty fields so that the default is set correctly
                keys_to_remove = []
                for key, value in input.items():
                    if (
                        isinstance(value, str) or not isinstance(value, Sequence)
                    ) and pd.isna(value):
                        keys_to_remove.append(key)
                for key in keys_to_remove:
                    input.pop(key)

                # validate fields
                if Manifest.col_datatype in input:
                    try:
                        input[Manifest.col_datatype] = pd.eval(
                            input[Manifest.col_datatype]
                        )
                    except Exception:
                        raise ValueError(
                            f"Invalid datatype: {input[Manifest.col_datatype]}"
                            ". Must be a list or left empty"
                        )

            return input

    @classmethod
    def load(cls, fpath: str | Path, validate=True, **kwargs) -> Manifest:
        """Load the manifest from a CSV file."""
        if "dtype" in kwargs:
            raise ValueError(
                "This function does not accept 'dtype' as a keyword argument."
            )
        df_manifest = Manifest(pd.read_csv(fpath, dtype=str, **kwargs))
        if validate:
            df_manifest = df_manifest._validate()
        return df_manifest

    def _validate(self):
        """Validate the manifest."""
        records = self.to_dict(orient="records")
        df_validated = Manifest(
            [self._Model(**record).model_dump() for record in records]
        )

        missing_cols = set(df_validated.columns) - set(self.columns)
        if len(missing_cols) > 0:
            raise ValueError(f"Invalid manifest (missing columns: {missing_cols})")

        for col in df_validated.columns:
            self.loc[:, col] = df_validated.loc[:, col]

        return self
