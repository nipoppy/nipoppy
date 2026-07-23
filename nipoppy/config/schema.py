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
        If schema version is newer than the one supported by this version of Nipoppy.
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


def get_earliest_schema_version(
    config_type: ConfigType,
) -> str:
    """Get the earliest schema version for a config type.

    If set as the default_factory in a Pydantic model, this will warn users when
    they are using a config file that does not include a schema version field.
    """
    logger.warning(
        f"{config_type.value.capitalize()} config is missing the required "
        f"{SCHEMA_VERSION_FIELD} field. Defaulting to the earliest known version "
        f"({EARLIEST_SCHEMA_VERSION}); this will become an error in a future Nipoppy "
        "release. Add the following field to the config:\n"
        f'"{SCHEMA_VERSION_FIELD}": "{EARLIEST_SCHEMA_VERSION}"'
    )
    return EARLIEST_SCHEMA_VERSION


def ensure_config_file_schema_version_exists(
    fpath_config: Path, config_type: ConfigType, strict: bool = False
) -> str:
    """Check if the current schema version for pipelines exists."""
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
                f"Pipeline configuration file {fpath_config} is missing "
                f"{SCHEMA_VERSION_FIELD} field."
            )
            current_version = get_current_schema_version(config_type)
            config[SCHEMA_VERSION_FIELD] = current_version

    return config[SCHEMA_VERSION_FIELD]
