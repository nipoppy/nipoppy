"""Pipeline configuration."""

import re
from pathlib import Path
from typing import Optional, Sequence

from pydantic import ConfigDict, Field, model_validator

from nipoppy.config.container import ModelWithContainerConfig


class PipelineConfig(ModelWithContainerConfig):
    """Model for processing pipeline configuration."""

    NAME: str = Field(description="Name of the pipeline")
    VERSION: str = Field(description="Version of the pipeline")
    DESCRIPTION: Optional[str] = Field(
        default=None, description="Free description field"
    )
    CONTAINER: Optional[Path] = Field(
        default=None,
        description=(
            "Path to the container associated with the pipeline"
            ", relative to the containers directory"  # TODO add default path
        ),
    )
    URI: Optional[str] = Field(
        default=None,
        description="The Docker or Apptainer/Singularity URI for the container",
    )
    DESCRIPTOR: Optional[dict] = Field(
        default=None,
        description=(
            "Descriptor for the pipeline, as a JSON object"
            ". Note: DESCRIPTOR and DESCRIPTOR_FILE cannot both be specified"
        ),
    )
    DESCRIPTOR_FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to the JSON descriptor file"
            ". Note: DESCRIPTOR_FILE and DESCRIPTOR cannot both be specified"
        ),
    )
    INVOCATION: Optional[dict] = Field(
        default=None,
        description="Invocation for the pipeline, as a JSON object",
    )
    # INVOCATION_FILE: Optional[Path] = None  # TODO
    PYBIDS_IGNORE: list[re.Pattern] = Field(
        default=[],
        description=(
            "List of regex patterns (strings) to ignore when "
            "building the PyBIDS layout"
        ),
    )
    TRACKER_CONFIG: dict[str, list[str]] = Field(
        default={},
        description="Configuration for the tracker associated with the pipeline",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_after(self):
        """
        Validate the pipeline configuration after creation.

        Specifically:
        - Check that <FIELD> and <FIELD>_FILE fields are not both set
        - Add an empty invocation if none is provided
        """
        field_pairs = [
            ("DESCRIPTOR", "DESCRIPTOR_FILE"),
            # ("INVOCATION", "INVOCATION_FILE"),
        ]
        for field_json, field_file in field_pairs:
            value_json = getattr(self, field_json)
            value_file = getattr(self, field_file)
            if value_json is not None and value_file is not None:
                raise ValueError(
                    f"Cannot specify both {field_json} and {field_file}"
                    f". Got {value_json} and {value_file} respectively."
                )

        # if self.INVOCATION is None and self.INVOCATION_FILE is None:
        if self.INVOCATION is None:
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


class BidsPipelineConfig(PipelineConfig):
    """
    Model for BIDS conversion pipeline configuration.

    This is the same as the :class:`nipoppy.config.pipeline.PipelineConfig` model
    except it requires an additional ``STEP`` field.
    """

    STEP: str = Field(description="Step name")
