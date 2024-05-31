"""Pipeline configuration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Sequence

from pydantic import ConfigDict, model_validator

from nipoppy.config.container import ModelWithContainerConfig


class PipelineConfig(ModelWithContainerConfig):
    """Model for workflow configuration."""

    DESCRIPTION: Optional[str] = None
    CONTAINER: Optional[Path] = None
    URI: Optional[str] = None
    DESCRIPTOR: Optional[dict] = None
    DESCRIPTOR_FILE: Optional[Path] = None
    INVOCATION: Optional[dict] = None
    INVOCATION_FILE: Optional[Path] = None
    PYBIDS_IGNORE: list[re.Pattern] = []
    TRACKER_CONFIG: dict[str, list[str]] = {}

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_fields(self):
        """
        Check that <FIELD> and <FIELD>_FILE fields are not both set.

        Also add an empty invocation if none is provided.
        """
        field_pairs = [
            ("DESCRIPTOR", "DESCRIPTOR_FILE"),
            ("INVOCATION", "INVOCATION_FILE"),
        ]
        for field_json, field_file in field_pairs:
            value_json = getattr(self, field_json)
            value_file = getattr(self, field_file)
            if value_json is not None and value_file is not None:
                raise ValueError(
                    f"Cannot specify both {field_json} and {field_file}"
                    f". Got {value_json} and {value_file} respectively."
                )

        if self.INVOCATION is None and self.INVOCATION_FILE is None:
            self.INVOCATION = {}

        return self

    def get_container(self) -> Path:
        """Return the path to the pipeline's container."""
        if self.CONTAINER is None:
            raise RuntimeError("No container specified for the pipeline")
        return self.CONTAINER

    def add_pybids_ignore_patterns(
        self,
        patterns: Sequence[str | re.Pattern] | str | re.Pattern,
    ):
        """Add pattern(s) to ignore for PyBIDS."""
        if isinstance(patterns, (str, re.Pattern)):
            patterns = [patterns]
        for pattern in patterns:
            if isinstance(pattern, str):
                pattern = re.compile(pattern)
            if pattern not in self.PYBIDS_IGNORE:
                self.PYBIDS_IGNORE.append(pattern)
