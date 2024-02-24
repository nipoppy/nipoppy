"""Generic class for tabular data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
from pydantic import BaseModel, ValidationError, model_validator


class _TabularModel(BaseModel):
    """
    Helper class for validating tabular data.

    Subclasses should define fields and their types,
    and optionally override the _validate_fields() method.
    """

    @model_validator(mode="before")
    @classmethod
    def _validate_input(cls, input: Any):
        """Validate the raw input."""
        if isinstance(input, dict):
            # generic validation
            # remove empty fields so that the default is set correctly
            keys_to_remove = []
            for key, value in input.items():
                if (
                    isinstance(value, str) or not isinstance(value, Sequence)
                ) and pd.isna(value):
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                input.pop(key)

            # model-specific validation
            # to be overridden in subclass if needed
            input = cls._validate_fields(input)

        return input

    @classmethod
    def _validate_fields(cls, input: dict):
        """Validate model-specific fields. To be overridden in subclass if needed."""
        return input


class _Tabular(pd.DataFrame, ABC):
    """
    Generic class with utilities for tabular data.

    See https://pandas.pydata.org/docs/development/extending.html.
    """

    @property
    @abstractmethod
    def model(self) -> type[_TabularModel]:
        """Model class associated with the tabular data."""
        raise NotImplementedError("model must be assigned in subclass")

    @classmethod
    def load(cls, fpath: str | Path, validate=True, **kwargs) -> _Tabular:
        """Load (and optionally validate) a tabular data file."""
        if "dtype" in kwargs:
            raise ValueError(
                "This function does not accept 'dtype' as a keyword argument"
                ". Everything is read as a string and validated later."
            )
        df = cls(pd.read_csv(fpath, dtype=str, **kwargs))
        if validate:
            df = df.validate()
        return df

    def validate(self) -> _Tabular:
        """Validate the dataframe based on the model."""
        records = self.to_dict(orient="records")
        try:
            df_validated = self.__class__(
                [self.model(**record).model_dump() for record in records]
            )

            missing_cols = set(df_validated.columns) - set(self.columns)
            if len(missing_cols) > 0:
                raise ValueError(f"Missing column(s): {missing_cols})")

        except Exception as exception:
            error_message = str(exception)
            if isinstance(exception, ValidationError):
                error_message += str(exception.errors())
            raise ValueError(
                f"Error when validating the {self.__class__.__name__.lower()}"
                f": {error_message}"
            )
        return df_validated

    def add_records(self, records: Sequence[dict]) -> _Tabular:
        """Add multiple records.

        Note that this creates a new object. The existing one is not modified.
        """
        for record in records:
            for key, value in record.items():
                if (
                    isinstance(value, Sequence) or not isinstance(value, str)
                ) or not pd.isna(value):
                    record[key] = str(value)
        new_records = [self.model(**record).model_dump() for record in records]
        records = self.to_dict(orient="records")
        records.extend(new_records)
        return self.__class__(records)

    def add_record(self, **kwargs) -> _Tabular:
        """Add a record.

        Note that this creates a new object. The existing one is not modified.
        """
        return self.add_records([kwargs])

    @property
    def _constructor(self):
        """Override pd.DataFrame._constructor to return the subclass."""
        return self.__class__

    @property
    def _constructor_sliced(self):
        """Override pd.DataFrame._constructor_sliced to return the series subclass."""
        return self.series_class

    @cached_property
    def series_class(self) -> type[pd.Series]:
        """Generator for the series subclass."""

        class _Series(pd.Series):
            @property
            def _constructor(_self):
                return _Series

            @property
            def _constructor_expanddim(_self):
                return self.__class__

        return _Series
