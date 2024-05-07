"""Dataset configuration."""

from pathlib import Path
from typing import Any, Optional, Self

from pydantic import ConfigDict, Field, model_validator

from nipoppy.config.container import ModelWithContainerConfig
from nipoppy.config.pipeline import PipelineConfig
from nipoppy.utils import check_session, load_json


class Config(ModelWithContainerConfig):
    """Model for dataset configuration."""

    DATASET_NAME: str = Field(description="Name of the dataset")
    VISITS: list[str] = Field(description="List of visits available in the study")
    SESSIONS: Optional[list[str]] = Field(
        default=None,
        description=(
            "List of sessions available in the study"
            " (inferred from VISITS if not given)"
        ),
    )
    BIDS: dict[str, dict[str, dict[str, PipelineConfig]]] = Field(
        default={}, description="Configurations for BIDS converters, if any"
    )
    PROC_PIPELINES: dict[str, dict[str, PipelineConfig]] = Field(
        description="Configurations for processing pipelines"
    )

    model_config = ConfigDict(extra="allow")

    def _check_no_duplicate_pipeline(self) -> Self:
        """Check that BIDS and PROC_PIPELINES do not have common pipelines."""
        bids_pipelines = set(self.BIDS.keys())
        proc_pipelines = set(self.PROC_PIPELINES.keys())
        if len(bids_pipelines & proc_pipelines) != 0:
            raise ValueError(
                "Cannot have the same pipeline under BIDS and PROC_PIPELINES"
                f", got {bids_pipelines} and {proc_pipelines}"
            )

    def _propagate_container_config(self) -> Self:
        """Propagate the container config to all pipelines."""

        def _propagate(pipeline_or_pipeline_dicts: dict | PipelineConfig):
            if isinstance(pipeline_or_pipeline_dicts, PipelineConfig):
                pipeline_config = pipeline_or_pipeline_dicts
                container_config = pipeline_config.get_container_config()
                if container_config.INHERIT:
                    container_config.merge_args_and_env_vars(self.CONTAINER_CONFIG)
            else:
                for (
                    child_pipeline_or_pipeline_dicts
                ) in pipeline_or_pipeline_dicts.values():
                    _propagate(child_pipeline_or_pipeline_dicts)

        _propagate(self.BIDS)
        _propagate(self.PROC_PIPELINES)

        return self

    @model_validator(mode="before")
    @classmethod
    def check_input(cls, data: Any):
        """Validate the raw input."""
        key_sessions = "SESSIONS"
        key_visits = "VISITS"
        if isinstance(data, dict):
            # if sessions are not given, infer from visits
            if key_sessions not in data:
                data[key_sessions] = [
                    check_session(visit) for visit in data[key_visits]
                ]

        return data

    @model_validator(mode="after")
    def validate_and_process(self) -> Self:
        """Validate and process the configuration."""
        self._check_no_duplicate_pipeline()
        self._propagate_container_config()
        return self

    def get_pipeline_config(
        self,
        pipeline_name: str,
        pipeline_version: str,
    ) -> PipelineConfig:
        """Get the config for a pipeline."""
        try:
            return self.PROC_PIPELINES[pipeline_name][pipeline_version]
        except KeyError:
            raise ValueError(f"No config found for {pipeline_name} {pipeline_version}")

    def get_bids_pipeline_config(
        self, pipeline_name: str, pipeline_version: str, pipeline_step: str
    ) -> PipelineConfig:
        """Get the config for a BIDS conversion pipeline."""
        try:
            return self.BIDS[pipeline_name][pipeline_version][pipeline_step]
        except KeyError:
            raise ValueError(
                "No config found for "
                f"{pipeline_name} {pipeline_version} {pipeline_step}"
            )

    def save(self, fpath: str | Path, **kwargs):
        """Save the config to a JSON file.

        Parameters
        ----------
        fpath : str | Path
            Path to the JSON file to write
        """
        fpath = Path(fpath)
        if "indent" not in kwargs:
            kwargs["indent"] = 4
        fpath.parent.mkdir(parents=True, exist_ok=True)
        with open(fpath, "w") as file:
            file.write(self.model_dump_json(**kwargs))

    @classmethod
    def load(cls, path: str | Path) -> Self:
        """Load a dataset configuration."""
        return cls(**load_json(path))
