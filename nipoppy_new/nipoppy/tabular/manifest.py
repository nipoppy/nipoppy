"""Class for the dataset manifest."""

from typing import Optional, Self

import pandas as pd
from pydantic import ConfigDict

from nipoppy.tabular.base import BaseTabular, BaseTabularModel


class ManifestModel(BaseTabularModel):
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

    # allow extra columns
    model_config = ConfigDict(extra="allow")


class Manifest(BaseTabular):
    """A dataset's manifest."""

    # column names
    col_participant_id = "participant_id"
    col_visit = "visit"
    col_session = "session"
    col_datatype = "datatype"

    index_cols = [col_participant_id, col_visit]

    # set the model
    model = ManifestModel

    _metadata = BaseTabular._metadata + [
        "col_participant_id",
        "col_visit",
        "col_session",
        "col_datatype",
        "index_cols",
        "model",
    ]

    @classmethod
    def load(cls, *args, sessions=None, visits=None, validate=True, **kwargs) -> Self:
        """Load the manifest."""
        manifest = super().load(*args, validate=validate, **kwargs)
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

    def get_imaging_subset(self, session: Optional[str] = None):
        """Get records with imaging data."""
        manifest = self[self[self.col_session].notna()]
        if session is not None:
            return manifest[manifest[self.col_session] == session]
        return manifest

    def get_participants_sessions(
        self, participant: Optional[str] = None, session: Optional[str] = None
    ):
        """Get participants and sessions."""
        if participant is None:
            participants = set(self[self.col_participant_id])
        else:
            participants = {participant}
        if session is None:
            sessions = self[self.col_session]
            sessions = set(sessions[sessions.notna()])
        else:
            sessions = {session}

        manifest_subset = self[
            (self[self.col_participant_id].isin(participants))
            & (self[self.col_session].isin(sessions))
        ]

        yield from manifest_subset[
            [self.col_participant_id, self.col_session]
        ].itertuples(index=False)
