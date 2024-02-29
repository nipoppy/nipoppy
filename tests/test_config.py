"""Tests for the config module."""

import json
from pathlib import Path

import pytest
from conftest import DPATH_TEST_DATA

from nipoppy.config import Config, load_config
from nipoppy.utils import FPATH_SAMPLE_CONFIG

REQUIRED_FIELDS = [
    "DATASET_NAME",
    "DATASET_ROOT",
    "CONTAINER_STORE",
    "SESSIONS",
]


def test_save(tmp_path: Path):
    fpath_out = tmp_path / "config.json"
    config = Config(
        DATASET_NAME="ds000001",
        DATASET_ROOT=DPATH_TEST_DATA,
        CONTAINER_STORE=tmp_path,
        SESSIONS=["ses-BL", "ses-M12"],
        BIDS={},
        PROC_PIPELINES={},
    )
    config.save(fpath_out)
    assert fpath_out.exists()
    with fpath_out.open("r") as file:
        assert isinstance(json.load(file), dict)


@pytest.mark.parametrize(
    "path",
    [
        FPATH_SAMPLE_CONFIG,
        DPATH_TEST_DATA / "config1.json",
        DPATH_TEST_DATA / "config2.json",
    ],
)
def test_load_config(path):
    config = load_config(path)
    assert isinstance(config, Config)
    for field in REQUIRED_FIELDS:
        getattr(config, field)


def test_load_config_missing_required():
    with pytest.raises(ValueError):
        load_config(DPATH_TEST_DATA / "config3-invalid.json")
