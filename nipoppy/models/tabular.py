"""Generic class for tabular data."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Self, Sequence

import pandas as pd
from pydantic import BaseModel, ValidationError, model_validator

from nipoppy.utils import save_df_with_backup


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

    _series_classes = {}
    sort_cols = None

    @property
    @abstractmethod
    def model(self) -> type[_TabularModel]:
        """Model class associated with the tabular data."""
        raise NotImplementedError("model must be assigned in subclass")

    @classmethod
    def load(cls, fpath: str | Path, validate=True, **kwargs) -> Self:
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

    def validate(self) -> Self:
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

    def add_records(self, records: Sequence[dict]) -> Self:
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

    def add_record(self, **kwargs) -> Self:
        """Add a record.

        Note that this creates a new object. The existing one is not modified.
        """
        return self.add_records([kwargs])

    def save_with_backup(
        self,
        fpath_symlink: str | Path,
        dname_backups: Optional[str] = None,
        use_relative_path=True,
        sort=True,
    ) -> Path | None:
        """Save the dataframe to a file with a backup."""
        if sort:
            tabular_new = self.sort_values()
        else:
            tabular_new = self
        if fpath_symlink.exists():
            tabular_old = self.load(fpath_symlink)
            if sort:
                tabular_old = tabular_old.sort_values()
            if tabular_new.equals(tabular_old):
                return None
        return save_df_with_backup(
            tabular_new,
            fpath_symlink,
            dname_backups,
            use_relative_path,
        )

    def equals(self, other: object) -> Self:
        try:
            pd.testing.assert_frame_equal(
                self,
                other,
                check_like=True,
                obj=str(self.__class__.__name__),
            )
            return True
        except AssertionError:
            return False

    def sort_values(self, **kwargs):
        """Sort the dataframe, by default on specific columns and ignoring the index."""
        sort_kwargs = {"by": self.sort_cols, "ignore_index": True}
        sort_kwargs.update(kwargs)
        return super().sort_values(**sort_kwargs)

    def get_series_class(self) -> type[pd.Series]:
        """Get the series class associated with a dataframe."""
        tabular_class_id = id(self.__class__)
        if tabular_class_id not in self._series_classes:

            class _Series(pd.Series):
                @property
                def _constructor(_self):
                    return _Series

                @property
                def _constructor_expanddim(_self):
                    return self.__class__

            self._series_classes[tabular_class_id] = _Series

        return self._series_classes[tabular_class_id]

    @property
    def _constructor(self) -> type[pd.DataFrame]:
        """Override pd.DataFrame._constructor to return the subclass."""
        return self.__class__

    @property
    def _constructor_sliced(self) -> type[pd.Series]:
        """Override pd.DataFrame._constructor_sliced to return the series subclass."""
        return self.get_series_class()
