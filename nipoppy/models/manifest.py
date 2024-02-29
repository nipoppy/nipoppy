"""Class for the dataset manifest."""

from typing import Optional, Self

import pandas as pd

from nipoppy.models.tabular import _Tabular, _TabularModel


class Manifest(_Tabular):
    """A dataset's manifest."""

    # column names
    col_participant_id = "participant_id"
    col_visit = "visit"
    col_session = "session"
    col_datatype = "datatype"

    index_cols = [col_participant_id, col_visit]

    class ManifestModel(_TabularModel):
        """Model for the manifest."""

        participant_id: str
        visit: str
        session: Optional[str]
        datatype: Optional[list[str]]

        @classmethod
        def validate_fields(cls, data: dict):
            """Validate manifest-specific fields."""
            datatype = data.get(Manifest.col_datatype)
            if datatype is not None and not isinstance(datatype, list):
                try:
                    data[Manifest.col_datatype] = pd.eval(datatype)
                except Exception:
                    raise ValueError(
                        f"Invalid datatype: {datatype} ({type(datatype)}))"
                        ". Must be a list, a string representation of a list"
                        ", or left empty"
                    )
            return data

    # set the model
    model = ManifestModel

    @classmethod
    def load(cls, *args, sessions=None, visits=None, **kwargs) -> Self:
        """Load the manifest."""
        manifest = super().load(*args, **kwargs)
        manifest.sessions = sessions
        manifest.visits = visits
        return manifest

    def __init__(self, *args, sessions=None, visits=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sessions = sessions
        self.visits = visits

    def validate(self, *args, **kwargs) -> Self:
        """Validate the manifest."""
        manifest = super().validate(*args, **kwargs)
        if self.sessions is not None:
            self._check_values(self.col_session, self.sessions)
        if self.visits is not None:
            self._check_values(self.col_visit, self.visits)
        return manifest

    def _check_values(self, col, allowed_values) -> Self:
        """Check that the column values are in the allowed values."""
        invalid_values = set(self[col]) - set(allowed_values)
        if len(invalid_values) > 0:
            raise ValueError(
                f"Invalid values for column {col}: {invalid_values}. "
                f"Expected only values from : {allowed_values}"
            )
        return self

    def get_imaging_only(self, session: Optional[str] = None):
        """Get records with imaging data."""
        manifest = self[self[self.col_session].notna()]
        if session is not None:
            return manifest[manifest[self.col_session] == session]
        return manifest
