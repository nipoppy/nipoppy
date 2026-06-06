"""Helpers for configuration schema version checks."""

from __future__ import annotations

from packaging.version import Version

from nipoppy.env import CURRENT_SCHEMA_VERSION
from nipoppy.exceptions import ConfigError

SCHEMA_VERSION_FIELD = "SCHEMA_VERSION"
DEFAULT_SCHEMA_VERSION = "1.0.0"


def check_schema_version(
    schema_version: str,
    current_version: CURRENT_SCHEMA_VERSION,
) -> None:
    """Validate SCHEMA_VERSION after model validation."""
    if Version(schema_version) > Version(current_version.value):  # noqa: E501
        raise ConfigError(
            f"{current_version.name} config uses schema version {schema_version}, which"
            " is newer than the schema version supported by this version of Nipoppy "
            f"({current_version.value}). Please upgrade Nipoppy."
        )
