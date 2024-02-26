"""Tests for the utils module."""

import json
from pathlib import Path

import pandas as pd
import pytest
from conftest import DPATH_TEST_DATA

from nipoppy.utils import load_json, save_df_with_backup, save_json


def test_load_json():
    assert isinstance(load_json(DPATH_TEST_DATA / "config1.json"), dict)


def test_save_json(tmp_path: Path):
    json_object = {"a": 1, "b": 2}
    fpath = tmp_path / "test.json"
    save_json(json_object, fpath)
    assert fpath.exists()
    with fpath.open("r") as file:
        assert json.load(file) == json_object


@pytest.mark.parametrize("dname_backups", [None, ".tests"])
@pytest.mark.parametrize(
    "fname,dname_backups_processed",
    [("test.csv", ".tests"), ("test2.csv", ".test2s")],
)
def test_save_df_with_backup(
    fname: str,
    dname_backups: str | None,
    dname_backups_processed: str,
    tmp_path: Path,
):
    fpath_symlink = tmp_path / fname
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    fpath_backup = save_df_with_backup(df, fpath_symlink, dname_backups)

    if dname_backups is None:
        dname_backups = dname_backups_processed

    assert fpath_symlink.exists()
    assert fpath_backup.exists()
    assert fpath_backup.parent == fpath_symlink.parent / dname_backups
