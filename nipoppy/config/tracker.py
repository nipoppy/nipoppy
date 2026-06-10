"""Tracker configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nipoppy.config.schema import (
    EARLIEST_SCHEMA_VERSION,
    check_current_schema_version,
    get_current_schema_version,
)
from nipoppy.env import ConfigType
from nipoppy.exceptions import ConfigError


class TrackerConfig(BaseModel):
    """Schema for tracker configuration."""

    SCHEMA_VERSION: str = Field(
        default=EARLIEST_SCHEMA_VERSION,
        description=(
            "Version of the schema used for this tracker configuration. The current "
            f"latest version is {get_current_schema_version(ConfigType.TRACKER)}"
        ),
    )
    PATHS: list[Path] = Field(
        description=(
            "List of at least one path to track. A path can include template "
            "strings for participant/session IDs and/or glob expressions"
        ),
    )

    PARTICIPANT_SESSION_DIR: Optional[Path] = Field(
        default=None,
        description=(
            "Path to the directory where participant-session results are expected"
        ),
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_after(self):
        """
        Validate the configuration after instantiation.

        Specifically:
        - Check schema version compatibility.
        - Make sure PATHS is not an empty list
        """
        check_current_schema_version(
            schema_version=self.SCHEMA_VERSION,
            config_type=ConfigType.TRACKER,
        )
        if len(self.PATHS) == 0:
            raise ConfigError(
                f"The tracker config must contain at least one path, got {self}"
            )
        return self
