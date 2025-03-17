"""Pipeline configuration."""

from __future__ import annotations

import warnings
from abc import ABC
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import to_jsonable_python

from nipoppy.config.container import ContainerInfo, _SchemaWithContainerConfig
from nipoppy.config.pipeline_step import (
    BasePipelineStepConfig,
    BidsPipelineStepConfig,
    ExtractionPipelineStepConfig,
    ProcPipelineStepConfig,
)
from nipoppy.env import DEFAULT_PIPELINE_STEP_NAME, PipelineTypeEnum
from nipoppy.utils import apply_substitutions_to_json


class PipelineInfo(BaseModel):
    """Schema for pipeline information."""

    NAME: str = Field(description="Name of the pipeline")
    VERSION: str = Field(description="Version of the pipeline")
    STEP: str = Field(
        description="Name of the pipeline step",
        default=DEFAULT_PIPELINE_STEP_NAME,
    )

    model_config = ConfigDict(extra="forbid")

    def __hash__(self):
        """Return a hash based on the pipeline's name, version and step."""
        return hash((self.NAME, self.VERSION, self.STEP))


class BasePipelineConfig(_SchemaWithContainerConfig, ABC):
    """Base schema for processing/BIDS pipeline configuration."""

    _expected_pipeline_type: Optional[PipelineTypeEnum] = None

    # for validation
    NAME: str = Field(description="Name of the pipeline")
    VERSION: str = Field(description="Version of the pipeline")
    DESCRIPTION: Optional[str] = Field(
        default=None, description="Free description field"
    )
    CONTAINER_INFO: ContainerInfo = Field(
        default=ContainerInfo(),
        description="Information about the container image file",
    )
    # Needed for validation
    STEPS: list[
        Union[
            BidsPipelineStepConfig, ProcPipelineStepConfig, ExtractionPipelineStepConfig
        ]
    ] = Field(
        default=[],
        description="List of pipeline step configurations",
    )
    PIPELINE_TYPE: Optional[PipelineTypeEnum] = None

    @model_validator(mode="before")
    @classmethod
    def validate_before(cls, data: Any) -> Any:
        """
        Validate the pipeline configuration before instantiation.

        Specifically:
        - Apply substitutions for pipeline name/version in the config
        """
        if isinstance(data, dict):
            substitutions = {}
            keys = ("NAME", "VERSION")
            for key in keys:
                if key in data:
                    substitutions[f"[[PIPELINE_{key}]]"] = data[key]
            data = apply_substitutions_to_json(to_jsonable_python(data), substitutions)

        return data

    @model_validator(mode="after")
    def validate_after(self):
        """
        Validate the pipeline configuration after creation.

        Specifically:
        - If STEPS has more than one item, make sure that each step has a unique name.
        - If _expected_pipeline_type is not None, make sure it matches PIPELINE_TYPE.
        """
        if len(self.STEPS) > 1:
            step_names = []
            for step in self.STEPS:
                if step.NAME is None:
                    raise ValueError(
                        "Found at least one step with undefined NAME field"
                        f" for pipeline {self.NAME} {self.VERSION}"
                        ". Pipeline steps must have names except "
                        "if there is only one step"
                    )
                if step.NAME in step_names:
                    raise ValueError(
                        f'Found at least two steps with NAME "{step.NAME}"'
                        f" for pipeline {self.NAME} {self.VERSION}"
                        ". Step names must be unique"
                    )
                step_names.append(step.NAME)

        if (self._expected_pipeline_type is not None) and (
            self.PIPELINE_TYPE != self._expected_pipeline_type
        ):
            raise ValueError(
                f"Expected pipeline type {self._expected_pipeline_type}"
                f" but got {self.PIPELINE_TYPE=} for pipeline "
                f"{self.NAME} {self.VERSION}"
            )

        return self

    def get_fpath_container(self) -> Path:
        """Return the path to the pipeline's container."""
        return self.CONTAINER_INFO.FILE

    def get_step_config(
        self, step_name: Optional[str] = None
    ) -> BasePipelineStepConfig:
        """
        Return the configuration for the given step.

        If step_name is None, return the configuration for the first step.
        """
        if len(self.STEPS) == 0:
            raise ValueError(
                f"No steps specified for pipeline {self.NAME} {self.VERSION}"
            )
        elif step_name is None:
            return self.STEPS[0]
        for step in self.STEPS:
            if step.NAME == step_name:
                return step
        raise ValueError(
            f"Step {step_name} not found in pipeline {self.NAME} {self.VERSION}"
        )


class BidsPipelineConfig(BasePipelineConfig):
    """Schema for BIDS pipeline configuration."""

    _expected_pipeline_type = PipelineTypeEnum.BIDSIFICATION

    STEPS: list[BidsPipelineStepConfig] = Field(
        default=[],
        description="List of pipeline step configurations",
    )
    model_config = ConfigDict(extra="forbid")


class ProcPipelineConfig(BasePipelineConfig):
    """Schema for processing pipeline configuration."""

    _expected_pipeline_type = PipelineTypeEnum.PROCESSING

    TRACKER_CONFIG_FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to the tracker configuration file associated with the pipeline"
            ". This file must contain a list of tracker configurations"
            ", each of which must be a dictionary with a NAME field (string)"
            " and a PATHS field (non-empty list of strings)"
        ),
    )
    STEPS: list[ProcPipelineStepConfig] = Field(
        default=[],
        description="List of pipeline step configurations",
    )
    model_config = ConfigDict(extra="forbid")


class ExtractionPipelineConfig(BasePipelineConfig):
    """Schema for extraction pipeline configuration."""

    _expected_pipeline_type = PipelineTypeEnum.EXTRACTION

    PROC_DEPENDENCIES: list[PipelineInfo] = Field(
        description=(
            "List of processing pipeline(s) (including step names) whose output "
            "the extraction pipeline depends on"
        )
    )
    STEPS: list[ExtractionPipelineStepConfig] = Field(
        default=[],
        description="List of pipeline step configurations",
    )
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_after(self):
        """
        Validate the config instantiation after instantiation.

        Specifically:
        - Make sure that PROC_DEPENDENCIES is not empty
        """
        if len(self.PROC_DEPENDENCIES) == 0:
            raise ValueError(
                "PROC_DEPENDENCIES is an empty list for extraction pipeline "
                f"{self.NAME} {self.VERSION}. Must have at least one dependency"
            )
        if len(set(self.PROC_DEPENDENCIES)) != len(self.PROC_DEPENDENCIES):
            warnings.warn(
                "PROC_DEPENDENCIES contains duplicate entries for extraction pipeline "
                f"{self.NAME} {self.VERSION}"
            )
        return self
