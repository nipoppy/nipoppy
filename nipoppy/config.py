"""Dataset configuration."""

from pathlib import Path
from typing import Optional, Self

from pydantic import BaseModel, ConfigDict, model_validator

from nipoppy.utils import load_json


class SingularityConfig(BaseModel):
    """Model for Singularity/Apptainer configuration."""

    COMMAND: str = "singularity"
    ARGS: list[str] = []
    ENV_VARS: dict[str, str] = {}

    model_config = ConfigDict(extra="forbid")


class PipelineConfig(BaseModel):
    """Model for workflow configuration."""

    CONTAINER: Optional[Path] = None
    URI: Optional[str] = None
    SINGULARITY_CONFIG: Optional[SingularityConfig] = None
    DESCRIPTOR: Optional[Path] = None
    INVOCATION: Optional[dict] = None
    PYBIDS_IGNORE: list[str] = []
    DESCRIPTION: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class Config(BaseModel):
    """Model for dataset configuration."""

    DATASET_NAME: str
    SESSIONS: list[str]
    VISITS: list[str] = []
    SINGULARITY_CONFIG: Optional[SingularityConfig] = SingularityConfig()
    BIDS: dict[str, dict[str, PipelineConfig]] = {}
    PROC_PIPELINES: dict[str, dict[str, PipelineConfig]]

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_no_duplicate_pipeline(self) -> Self:
        """Check that BIDS and PROC_PIPELINES do not have common pipelines."""
        bids_pipelines = set(self.BIDS.keys())
        proc_pipelines = set(self.PROC_PIPELINES.keys())
        print(bids_pipelines)
        print(proc_pipelines)
        if len(bids_pipelines & proc_pipelines) != 0:
            raise ValueError(
                "Cannot have the same pipeline under BIDS and PROC_PIPELINES"
                f", got {bids_pipelines} and {proc_pipelines}"
            )

    def save(self, fpath: str | Path, **kwargs):
        """Save the config to a JSON file.

        Parameters
        ----------
        fpath : str | Path
            Path to the JSON file to write
        """
        if "indent" not in kwargs:
            kwargs["indent"] = 4
        with open(fpath, "w") as file:
            file.write(self.model_dump_json(**kwargs))

    def get_pipeline_config(
        self, pipeline_name: str, pipeline_version: str
    ) -> PipelineConfig:
        """Get the config for a pipeline."""
        try:
            if pipeline_name in self.BIDS:
                return self.BIDS[pipeline_name][pipeline_version]
            else:
                return self.PROC_PIPELINES[pipeline_name][pipeline_version]
        except KeyError:
            raise ValueError(f"No config found for {pipeline_name} {pipeline_version}")


def load_config(path: str | Path) -> Config:
    """Load a dataset configuration."""
    return Config(**load_json(path))
