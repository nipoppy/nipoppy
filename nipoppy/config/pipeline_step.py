"""Pipeline step configuration."""

from __future__ import annotations

from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import ConfigDict, Field, model_validator
from pydantic_core import to_jsonable_python

from nipoppy.config.container import _SchemaWithContainerConfig
from nipoppy.env import DEFAULT_PIPELINE_STEP_NAME
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.utils import apply_substitutions_to_json


class AnalysisLevelType(str, Enum):
    """Pipeline step types."""

    participant_session = "participant_session"
    participant = "participant"
    session = "session"
    group = "group"


class BasePipelineStepConfig(_SchemaWithContainerConfig, ABC):
    """Schema for processing pipeline step configuration."""

    NAME: str = Field(
        default=DEFAULT_PIPELINE_STEP_NAME,
        description="Step name. Required if the pipeline has multiple steps",
    )
    DESCRIPTOR_FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to the JSON descriptor file. Only needed for custom pipelines "
        ),
    )
    INVOCATION_FILE: Optional[Path] = Field(
        default=None,
        description="Path to the JSON invocation file",
    )
    ANALYSIS_LEVEL: AnalysisLevelType = Field(
        default=AnalysisLevelType.participant_session,
        description=(
            "Analysis level of the pipeline step. This controls the granularity of "
            "the loop over subjects and sessions. By default, pipeline runners will "
            "loop over all subjects and sessions, but this field field can be set to "
            f'"{AnalysisLevelType.participant}" to loop over subjects only, '
            f'"{AnalysisLevelType.session}" to loop over sessions only, '
            f"and {AnalysisLevelType.group} to only run the pipeline a single time."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def validate_before(cls, data: Any) -> Any:
        """
        Validate the pipeline step configuration before instantiation.

        Specifically:
        - Apply substitutions for step name in the config
        """
        if isinstance(data, dict):
            if data.get("NAME") is not None:
                data = apply_substitutions_to_json(
                    to_jsonable_python(data), {"[[STEP_NAME]]": data["NAME"]}
                )
        return data


class ProcPipelineStepConfig(BasePipelineStepConfig):
    """Schema for processing pipeline step configuration."""

    TRACKER_CONFIG_FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to the tracker configuration file associated with the pipeline step"
        ),
    )
    PYBIDS_IGNORE_FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to file containing a list of regex patterns (strings) to ignore "
            "when building the PyBIDS layout"
        ),
    )
    GENERATE_PYBIDS_DATABASE: Optional[bool] = Field(
        default=True,
        description=(
            "Whether or not to generate a PyBIDS database as part of the pipeline step"
            " (default: true)"
        ),
    )
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_after(self):
        """
        Validate the pipeline step configuration after creation.

        Specifically:
        - Make sure that the tracker configuration file is not set if the analysis
        level is not participant_session
        """
        if (
            self.ANALYSIS_LEVEL != AnalysisLevelType.participant_session
            and self.TRACKER_CONFIG_FILE is not None
        ):
            raise ValueError(
                "TRACKER_CONFIG_FILE cannot be set if ANALYSIS_LEVEL is not "
                f"{AnalysisLevelType.participant_session}"
            )
        return self


class BidsPipelineStepConfig(BasePipelineStepConfig):
    """Schema for BIDS pipeline step configuration."""

    UPDATE_DOUGHNUT: Optional[bool] = Field(
        default=False,
        description=(
            f"Whether or not the {Doughnut.col_in_bids} column "
            "in the doughnut file should be updated"
        ),
    )
    model_config = ConfigDict(extra="forbid")
