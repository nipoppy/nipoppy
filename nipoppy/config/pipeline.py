"""Pipeline configuration."""

import re
from pathlib import Path
from typing import Optional, Sequence

from pydantic import ConfigDict

from nipoppy.config.singularity import ModelWithSingularityConfig


class PipelineConfig(ModelWithSingularityConfig):
    """Model for workflow configuration."""

    CONTAINER: Optional[Path] = None
    URI: Optional[str] = None
    DESCRIPTOR: Optional[dict] = None
    INVOCATION: Optional[dict] = None
    PYBIDS_IGNORE: list[re.Pattern] = []
    DESCRIPTION: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

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
