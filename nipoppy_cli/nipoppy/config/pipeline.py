"""Pipeline configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, Field, model_validator

from nipoppy.config.container import ContainerInfo, SchemaWithContainerConfig
from nipoppy.config.pipeline_step import PipelineStepConfig


class PipelineConfig(SchemaWithContainerConfig):
    """Schema for processing pipeline configuration."""

    NAME: str = Field(description="Name of the pipeline")
    VERSION: str = Field(description="Version of the pipeline")
    DESCRIPTION: Optional[str] = Field(
        default=None, description="Free description field"
    )
    CONTAINER_INFO: ContainerInfo = Field(
        default=ContainerInfo(),
        description="Information about the container image file",
    )
    STEPS: list[PipelineStepConfig] = Field(
        default=[],
        description="List of pipeline step configurations",
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
        - If STEPS has more than one item, make sure that each step has a unique name.
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
                        ". Pipeline names must be unique"
                    )
                step_names.append(step.NAME)

        return self

    def get_container(self) -> Path:
        """Return the path to the pipeline's container."""
        if self.CONTAINER_INFO.PATH is None:
            raise RuntimeError("No container specified for the pipeline")
        return self.CONTAINER_INFO.PATH

    def get_step_config(self, step_name: Optional[str] = None) -> PipelineStepConfig:
        """
        Return the configuration for the given step.

        If step_name is None, return the configuration for the first step.
        """
        if step_name is None:
            return self.STEPS[0]
        for step in self.STEPS:
            if step.NAME == step_name:
                return step
        raise ValueError(
            f"Step {step_name} not found in pipeline {self.NAME} {self.VERSION}"
        )

    def get_invocation_file(self, step_name: Optional[str] = None) -> Path:
        """
        Return the path to the invocation file for the given step.

        Is step is None, return the invocation file for the first step.
        """
        return self.get_step_config(step_name).INVOCATION_FILE

    def get_descriptor_file(self, step_name: Optional[str] = None) -> Path:
        """
        Return the path to the descriptor file for the given step.

        If step is None, return the descriptor file for the first step.
        """
        return self.get_step_config(step_name).DESCRIPTOR_FILE
