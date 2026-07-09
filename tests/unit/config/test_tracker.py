"""Tests for TrackerConfig class."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from nipoppy.config.schema import EARLIEST_SCHEMA_VERSION
from nipoppy.config.tracker import TrackerConfig

FIELDS_STEP = [
    "SCHEMA_VERSION",
    "PATHS",
    "PARTICIPANT_SESSION_DIR",
]


@pytest.mark.parametrize(
    "data",
    [
        {"PATHS": ["path1", "path2"]},
    ],
)
def test_fields(data):
    tracker_config = TrackerConfig(**data)
    for field in FIELDS_STEP:
        assert hasattr(tracker_config, field)

    assert len(set(tracker_config.model_dump())) == len(FIELDS_STEP)


def test_no_extra_field():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        TrackerConfig(not_a_field="a")


def test_schema_version_default():
    tracker_config = TrackerConfig(PATHS=["path1"])
    assert tracker_config.SCHEMA_VERSION == EARLIEST_SCHEMA_VERSION


def test_error_invalid_schema_version():
    with pytest.raises(
        ValidationError,
        match="Invalid schema version:",
    ):
        TrackerConfig(PATHS=["path1"], SCHEMA_VERSION="invalid_version")


def test_schema_version_newer():
    with pytest.raises(ValueError, match="newer than the latest schema version"):
        TrackerConfig(PATHS=[Path("path1")], SCHEMA_VERSION="999.0.0")


def test_at_least_one_path():
    with pytest.raises(ValueError, match="must contain at least one path"):
        TrackerConfig(PATHS=[])
