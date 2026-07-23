"""Tests for TrackerConfig class."""

import functools

import pytest

from nipoppy.config.schema import get_earliest_schema_version
from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import ConfigType

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


def test_schema_version_default_factory():
    default_factory = TrackerConfig.model_fields["SCHEMA_VERSION"].default_factory

    assert isinstance(default_factory, functools.partial)
    assert default_factory.func is get_earliest_schema_version
    assert default_factory.keywords == {"config_type": ConfigType.TRACKER}


def test_at_least_one_path():
    with pytest.raises(ValueError, match="must contain at least one path"):
        TrackerConfig(PATHS=[])
