"""Tests for configuration schema version helpers."""

import pytest

from nipoppy.config.schema import (
    EARLIEST_SCHEMA_VERSION,
    ensure_schema_support,
    get_earliest_schema_version,
)
from nipoppy.env import ConfigType
from nipoppy.exceptions import ConfigError


@pytest.mark.parametrize("config_type", ConfigType)
def test_get_earliest_schema_version(
    config_type: ConfigType, caplog: pytest.LogCaptureFixture
):
    assert get_earliest_schema_version(config_type) == EARLIEST_SCHEMA_VERSION
    assert "Defaulting to the earliest known version" in caplog.text


@pytest.mark.parametrize("config_type", ConfigType)
def test_error_invalid_schema_version(config_type: ConfigType):
    with pytest.raises(ConfigError, match="Invalid schema version:"):
        ensure_schema_support("invalid_version", config_type)


@pytest.mark.parametrize("config_type", ConfigType)
def test_schema_version_newer(config_type: ConfigType):
    with pytest.raises(
        ConfigError,
        match="newer than the latest schema version supported",
    ):
        ensure_schema_support("999.0.0", config_type)
