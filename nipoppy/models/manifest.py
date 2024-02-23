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

    sessions = None
    visits = None

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

    @classmethod
    def load(cls, *args, sessions=None, visits=None, **kwargs) -> Manifest:
        """Load the manifest."""
        manifest: Manifest = super().load(*args, **kwargs)
        manifest.sessions = sessions
        manifest.visits = visits
        return manifest

    def add_record(self, **kwargs) -> Manifest:
        """
        Add a record to the manifest.

        Note that this creates a new Manifest object. The existing one is not modified.
        """
        return super().add_record(**kwargs)

    def validate(self) -> Manifest:
        """Validate the manifest."""
        manifest = super().validate()
        if self.sessions is not None:
            self._check_values(self.col_session, self.sessions)
        if self.visits is not None:
            self._check_values(self.col_visit, self.visits)
        return manifest

    def _check_values(self, col, allowed_values):
        """Check that the column values are in the allowed values."""
        invalid_values = set(self[col]) - set(allowed_values)
        if len(invalid_values) > 0:
            raise ValueError(
                f"Invalid values for column {col}: {invalid_values}. "
                f"Expected only values from : {allowed_values}"
            )
        return self
