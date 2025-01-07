"""Tracker configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrackerConfig(BaseModel):
    """Schema for tracker configuration."""

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
        - Make sure PATHS is not an empty list
        """
        if len(self.PATHS) == 0:
            raise ValueError(
                f"The tracker config must contain at least one path, got {self}"
            )
        return self
