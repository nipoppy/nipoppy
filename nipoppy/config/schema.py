"""Helpers for configuration schema version checks."""

from __future__ import annotations

from packaging.version import InvalidVersion, Version

from nipoppy.env import SCHEMA_VERSION_INFO, ConfigType
from nipoppy.exceptions import ConfigError

SCHEMA_VERSION_FIELD = "SCHEMA_VERSION"
EARLIEST_SCHEMA_VERSION = "1.0.0"


def get_current_schema_version(config_type: ConfigType) -> str:
    """Get the current schema version for a configuration type."""
    return SCHEMA_VERSION_INFO[config_type]["current"]


def check_current_schema_version(
    schema_version: str,
    config_type: ConfigType,
) -> None:
    """Validate schema version is supported by this version of Nipoppy.

    Raises
    ------
    ConfigError
        If schema version is newer than the one supported by this version of Nipoppy.
    """
    current_version = get_current_schema_version(config_type)
    try:
        is_newer = Version(schema_version) > Version(current_version)
    except InvalidVersion as exception:
        raise ConfigError(f"Invalid schema version: {schema_version}") from exception

    if is_newer:  # noqa: E501
        raise ConfigError(
            f"{config_type.value.capitalize()} config uses schema version "
            f"{schema_version}, which is newer than the schema version supported by "
            f"this version of Nipoppy ({current_version}). Please upgrade Nipoppy."
        )
