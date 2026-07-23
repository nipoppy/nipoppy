"""Tests for configuration schema version helpers."""

import pytest

from nipoppy.config.schema import (
    EARLIEST_SCHEMA_VERSION,
    ensure_config_file_schema_version_exists,
    ensure_schema_support,
    get_current_schema_version,
    get_earliest_schema_version,
)
from nipoppy.env import ConfigType
from nipoppy.exceptions import ConfigError
from tests.conftest import DPATH_TEST_DATA


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


def test_config_file_requires_schema_version():
    fpath_config = DPATH_TEST_DATA / "pipeline_config-no-schema-version.json"

    with pytest.raises(ConfigError, match="must include SCHEMA_VERSION"):
        ensure_config_file_schema_version_exists(
            fpath_config, ConfigType.PIPELINE, strict=True
        )


def test_config_file_warns_no_schema_version(caplog: pytest.LogCaptureFixture):
    fpath_config = DPATH_TEST_DATA / "pipeline_config-no-schema-version.json"

    schema_version = ensure_config_file_schema_version_exists(
        fpath_config, ConfigType.PIPELINE
    )

    assert schema_version == get_current_schema_version(ConfigType.PIPELINE)
    assert any(
        "is missing SCHEMA_VERSION field" in record.message for record in caplog.records
    )
