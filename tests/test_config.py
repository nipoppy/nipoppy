"""Tests for the config module."""
import pytest
from conftest import DPATH_TEST_DATA

from nipoppy.models.config import Config, load_config
from nipoppy.utils import FPATH_SAMPLE_CONFIG

REQUIRED_FIELDS = [
    "DATASET_NAME",
    "DATASET_ROOT",
    "CONTAINER_STORE",
    "SESSIONS",
]


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
