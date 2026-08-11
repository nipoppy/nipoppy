"""Tests for TrackerConfig class."""

import pytest

from nipoppy.core._models.config.schema import EARLIEST_SCHEMA_VERSION
from nipoppy.core._models.config.tracker import TrackerConfig

FIELDS_TRACKER = [
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
    for field in FIELDS_TRACKER:
        assert hasattr(tracker_config, field)

    assert len(set(tracker_config.model_dump())) == len(FIELDS_TRACKER)


def test_no_extra_field():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        TrackerConfig(not_a_field="a")


def test_schema_version_default_schema_version():
    config = TrackerConfig(PATHS=["path1"])
    assert config.SCHEMA_VERSION == EARLIEST_SCHEMA_VERSION


def test_at_least_one_path():
    with pytest.raises(ValueError, match="must contain at least one path"):
        TrackerConfig(PATHS=[])
