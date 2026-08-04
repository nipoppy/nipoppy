"""Helpers for configuration schema version checks."""

from __future__ import annotations

from pathlib import Path

from packaging.version import InvalidVersion, Version

from nipoppy.env import SCHEMA_VERSION_INFO, ConfigType
from nipoppy.exceptions import ConfigError
from nipoppy.logger import get_logger
from nipoppy.utils.utils import load_json

logger = get_logger()


SCHEMA_VERSION_FIELD = "SCHEMA_VERSION"
EARLIEST_SCHEMA_VERSION = "1.0"


def get_current_schema_version(config_type: ConfigType) -> str:
    """Get the current schema version for a configuration type."""
    return SCHEMA_VERSION_INFO[config_type]["current"]


def ensure_schema_support(
    schema_version: str,
    config_type: ConfigType,
) -> str:
    """Validate schema version is supported by this version of Nipoppy.

    Raises
    ------
    ConfigError
        If schema version is invalid or newer than the one supported by this version of Nipoppy.
    """
    current_version = get_current_schema_version(config_type)
    try:
        is_newer = Version(schema_version) > Version(current_version)
    except InvalidVersion as exception:
        raise ConfigError(f"Invalid schema version: {schema_version}") from exception

    if is_newer:
        raise ConfigError(
            f"{config_type.value.capitalize()} config uses schema version "
            f"{schema_version}, which is newer than the latest schema version supported"
            f" by this version of Nipoppy ({current_version}). Please upgrade Nipoppy."
        )

    return schema_version


def ensure_config_file_schema_version_exists(
    fpath_config: Path, config_type: ConfigType, strict: bool = False
) -> str:
    """Check if the schema version field is set."""
    config = load_json(fpath_config)

    if SCHEMA_VERSION_FIELD not in config:
        if strict:
            raise ConfigError(
                f"Pipeline configuration file {fpath_config} must include "
                f"{SCHEMA_VERSION_FIELD} field with an explicit version, but it is"
                " missing"
            )
        else:
            logger.warning(
                f"{fpath_config} is missing the required {SCHEMA_VERSION_FIELD} field; "
                f"assuming version {EARLIEST_SCHEMA_VERSION}. This will become an "
                f"error in a future Nipoppy release. To silence this warning, add the following to the config: "
                f'"{SCHEMA_VERSION_FIELD}": "{EARLIEST_SCHEMA_VERSION}"'
            )
            current_version = get_current_schema_version(config_type)
            config[SCHEMA_VERSION_FIELD] = current_version

    return config[SCHEMA_VERSION_FIELD]
