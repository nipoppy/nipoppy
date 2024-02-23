"""Tests for the tabular module."""

from contextlib import nullcontext

import pandas as pd
import pytest
from conftest import DPATH_TEST_DATA

from nipoppy.models.tabular import _Tabular, _TabularModel


class Tabular(_Tabular):
    model = _TabularModel


class TabularWithModel(_Tabular):
    class _Model(_TabularModel):
        a: str
        b: int = 0

    model = _Model


@pytest.mark.parametrize(
    "fpath",
    [
        DPATH_TEST_DATA / "manifest1.csv",
        DPATH_TEST_DATA / "manifest2.csv",
        DPATH_TEST_DATA / "manifest3-invalid.csv",
        DPATH_TEST_DATA / "manifest4-invalid.csv",
    ],
)
@pytest.mark.parametrize("tabular_class", [Tabular, TabularWithModel])
def test_load(fpath, tabular_class: _Tabular):
    assert isinstance(tabular_class.load(fpath, validate=False), tabular_class)


@pytest.mark.parametrize("dtype", [str, int])
def test_load_error(dtype):
    with pytest.raises(ValueError):
        Tabular.load(DPATH_TEST_DATA / "manifest1.csv", dtype=dtype)


@pytest.mark.parametrize(
    "data,is_valid",
    [
        ([{"a": "A", "b": 1}], True),
        ([{"a": "AA", "b": pd.NA}], True),
        ([{"a": "AAA", "b": None}], True),
        ([{"a": "A", "b": "0"}], True),
        ([{"a": 1, "b": 1}], False),
        ([{"a": "A", "b": "b"}], False),
    ],
)
def test_validate(data, is_valid):
    tabular = TabularWithModel(data)
    with pytest.raises(ValueError) if not is_valid else nullcontext():
        assert isinstance(tabular.validate(), TabularWithModel)


def test_validate_all_fields_present():
    tabular = TabularWithModel([{"a": "A"}])
    with pytest.raises(ValueError):
        assert isinstance(tabular.validate(), TabularWithModel)


@pytest.mark.parametrize(
    "data",
    [
        {"a": "A", "b": "1"},
        {"a": "A", "b": 1},
    ],
)
def test_add_record(data: dict):
    tabular = TabularWithModel().add_record(**data)
    assert len(tabular) == 1
    assert isinstance(tabular, TabularWithModel)


def test_constructor_overrides():
    colnames = ["a", "b"]
    data = {colname: [colname] + [pd.NA] for colname in colnames}
    tabular = Tabular(data)

    assert isinstance(tabular[colnames[0]].to_frame(), Tabular)
    assert isinstance(tabular.fillna("x"), Tabular)
