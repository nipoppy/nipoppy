"""Tests for the utils module."""

import json
from pathlib import Path

from conftest import DPATH_TEST_DATA

from nipoppy.utils import load_json, save_json


def test_load_json():
    assert isinstance(load_json(DPATH_TEST_DATA / "config1.json"), dict)


def test_save_json(tmp_path: Path):
    json_object = {"a": 1, "b": 2}
    fpath = tmp_path / "test.json"
    save_json(json_object, fpath)
    assert fpath.exists()
    with fpath.open("r") as file:
        assert json.load(file) == json_object
