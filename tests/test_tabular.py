"""Tests for the tabular module."""

from contextlib import nullcontext
from pathlib import Path

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
    sort_cols = ["b"]


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


@pytest.mark.parametrize(
    "data",
    [
        [{"a": "A", "b": "1"}],
        [{"a": "A", "b": "1"}, {"a": "A", "b": 1}],
    ],
)
def test_add_records(data: list[dict]):
    tabular = TabularWithModel().add_records(data)
    assert len(tabular) == len(data)
    assert isinstance(tabular, TabularWithModel)


@pytest.mark.parametrize("dname_backups", [None, ".tests"])
@pytest.mark.parametrize(
    "fname,dname_backups_processed",
    [("test.csv", ".tests"), ("test2.csv", ".test2s")],
)
def test_save_with_backup(
    fname: str,
    dname_backups: str | None,
    dname_backups_processed: str,
    tmp_path: Path,
):
    fpath_symlink = tmp_path / fname
    tabular = TabularWithModel([{"a": "A", "b": 1}])
    fpath_backup = tabular.save_with_backup(fpath_symlink, dname_backups)

    if dname_backups is None:
        dname_backups = dname_backups_processed

    assert fpath_symlink.exists()
    assert fpath_symlink.is_symlink()
    assert fpath_backup.exists()
    assert fpath_backup.parent == fpath_symlink.parent / dname_backups
    assert isinstance(TabularWithModel.load(fpath_symlink), TabularWithModel)


@pytest.mark.parametrize(
    "data1,data2",
    [
        ([{"a": "A", "b": 1}], [{"a": "A", "b": 1}]),
        (
            [{"a": "a", "b": 1}, {"a": "a", "b": 2}],
            [{"a": "a", "b": 2}, {"a": "a", "b": 1}],
        ),
    ],
)
def test_save_with_backup_no_change(data1, data2, tmp_path: Path):
    fpath_symlink = tmp_path / "test.csv"
    tabular1 = TabularWithModel(data1)
    fpath_backup1 = tabular1.save_with_backup(fpath_symlink)
    assert fpath_backup1 is not None
    tabular2 = TabularWithModel(data2)
    assert tabular2.save_with_backup(fpath_symlink) is None
    assert len(list(fpath_backup1.parent.iterdir())) == 1


@pytest.mark.parametrize(
    "data1,data2,equal",
    [
        ([{"a": "A", "b": 1}], [{"a": "A", "b": 1}], True),
        ([{"a": "A", "b": 1}], [{"a": "A", "b": 2}], False),
        ([{"a": "A", "b": [1]}], [{"a": "A", "b": [1]}], True),
        ([{"a": "A", "b": [1]}], [{"a": "A", "b": [1, 2]}], False),
        ([{"a": "A", "b": 1}], [{"b": 1, "a": "A"}], True),
        ([{"a": "A"}, {"a": "a"}], [{"a": "a"}, {"a": "A"}], False),
    ],
)
def test_equals(data1, data2, equal):
    tabular1 = Tabular(data1)
    tabular2 = Tabular(data2)
    if equal:
        assert tabular1.equals(tabular2)
    else:
        assert not tabular1.equals(tabular2)


@pytest.mark.parametrize(
    "data_before,data_after,ascending",
    [
        (
            [{"a": "A", "b": 2}, {"a": "A", "b": 1}],
            [{"a": "A", "b": 1}, {"a": "A", "b": 2}],
            True,
        ),
        (
            [{"a": "A", "b": 1}, {"a": "A", "b": 2}],
            [{"a": "A", "b": 2}, {"a": "A", "b": 1}],
            False,
        ),
    ],
)
@pytest.mark.parametrize("inplace", [False, True])
def test_sort_values(data_before, data_after, ascending, inplace):
    tabular = TabularWithModel(data_before)
    tabular_sorted = tabular.sort_values(ascending=ascending, inplace=inplace)
    if inplace:
        assert tabular_sorted is None
        tabular_sorted = tabular
    assert isinstance(tabular_sorted, TabularWithModel)
    pd.testing.assert_frame_equal(tabular_sorted, TabularWithModel(data_after))


def test_constructor_overrides():
    colnames = ["a", "b"]
    data = {colname: [colname] + [pd.NA] for colname in colnames}
    tabular = Tabular(data)

    assert isinstance(tabular[colnames[0]].to_frame(), Tabular)
    assert isinstance(tabular.fillna("x"), Tabular)
