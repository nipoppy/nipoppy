"""Container (i.e., Singularity/Apptainer) configuration model and utility functions."""

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nipoppy.env import ContainerCommandEnum


class ContainerConfig(BaseModel):
    """
    Schema for container configuration.

    Does not include information about the container image.
    """

    COMMAND: Optional[ContainerCommandEnum] = Field(
        default=ContainerCommandEnum.APPTAINER,
        description=(
            "Name of container engine. If null/None, the pipeline will not run in a "
            "container (e.g., baremetal installations)."
        ),
    )
    BIND_PATHS: list[Path] = Field(
        default=[], description="Paths to bind inside the container"
    )
    ENV_VARS: dict[str, str] = Field(
        default={},
        description=(
            "Environment variables that should be available inside the container"
        ),
    )
    ARGS: list[str] = Field(
        default=[],
        description=(
            "Additional arguments for Apptainer/Singularity/Docker call"
            ". Note: bind paths and environment variables should be specified using "
            "BIND_PATHS and ENV_VARS respectively."
        ),
    )
    INHERIT: bool = Field(
        default=True,
        description=(
            "Whether this config should inherit from higher-lever container configs."
            " If false, will ignore higher-level configs"
        ),
    )

    model_config = ConfigDict(extra="forbid")

    def merge(self, other: Any, overwrite_command=False):
        """
        Combine with another ContainerConfig instance.

        By default this only changes arguments and environment variables, and no
        information is overwritten:
        - Arguments from other are appended to arguments of the current instance
        - Environment variables from other do not overwrite those of the current
        instance

        If overwrite_command is True, the command of the current instance is
        replaced with that of the other instance.
        """
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot merge {self.__class__} with object of type {type(other)}"
            )

        if overwrite_command:
            self.COMMAND = other.COMMAND

        if self.ARGS != other.ARGS:
            self.ARGS.extend(other.ARGS)

        for env_var, value in other.ENV_VARS.items():
            if env_var not in self.ENV_VARS:
                self.ENV_VARS[env_var] = value

        return self


class ContainerInfo(BaseModel):
    """Schema for container image (i.e., file) information."""

    FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to the container associated with the pipeline"
            ", relative to the root directory of the dataset"
        ),
    )
    URI: Optional[str] = Field(
        default=None,
        description="The Docker or Apptainer/Singularity URI for the container",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_after(self):
        """
        Validate the container info after instantiation.

        Specifically:

        - If URI is specified, FILE must also be specified
        """
        if self.URI is not None and self.FILE is None:
            raise ValueError(
                f"FILE must be specified if URI is set, got {self.FILE} and "
                f"{self.URI} respectively"
            )
        return self


class _SchemaWithContainerConfig(BaseModel):
    """To be inherited by configs that have a ContainerConfig sub-config."""

    CONTAINER_CONFIG: ContainerConfig = Field(
        default=ContainerConfig(),
        description="Configuration for running a container",
    )

    def get_container_config(self) -> ContainerConfig:
        """Return the pipeline's ContainerConfig object."""
        return self.CONTAINER_CONFIG
