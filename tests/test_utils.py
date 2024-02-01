"""Tests for the utils module."""
from conftest import DPATH_TEST_DATA

from nipoppy.utils import load_json


def test_load_json():
    assert isinstance(load_json(DPATH_TEST_DATA / "config1.json"), dict)
