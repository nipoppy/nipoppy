"""Tracker configuration."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Annotated, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from nipoppy.config.schema import (
    ensure_schema_support,
    get_current_schema_version,
    get_earliest_schema_version,
)
from nipoppy.env import ConfigType
from nipoppy.exceptions import ConfigError


class TrackerConfig(BaseModel):
    """Schema for tracker configuration."""

    SCHEMA_VERSION: Annotated[
        str,
        AfterValidator(
            functools.partial(
                ensure_schema_support,
                config_type=ConfigType.TRACKER,
            )
        ),
    ] = Field(
        default_factory=functools.partial(
            get_earliest_schema_version,
            config_type=ConfigType.TRACKER,
        ),
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
        if len(self.PATHS) == 0:
            raise ConfigError(
                f"The tracker config must contain at least one path, got {self}"
            )
        return self
