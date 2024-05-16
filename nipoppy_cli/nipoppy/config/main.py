"""Dataset configuration."""

import json
from pathlib import Path
from typing import Any, Callable, Optional, Self, Tuple

from pydantic import ConfigDict, Field, model_validator

from nipoppy.config.container import ModelWithContainerConfig
from nipoppy.config.pipeline import BidsPipelineConfig, PipelineConfig
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
    GLOBALS: dict[str, str] = Field(
        default={},
        description=(
            "Top-level mapping for replacing placeholder expressions in the rest "
            "of the config file. Note: the replacement only happens if the config "
            "is loaded from a file with :func:`nipoppy.config.main.Config.load`"
        ),
    )
    BIDS_PIPELINES: list[BidsPipelineConfig] = Field(
        default=[], description="Configurations for BIDS conversion, if applicable"
    )
    PROC_PIPELINES: list[PipelineConfig] = Field(
        description="Configurations for processing pipelines"
    )

    model_config = ConfigDict(extra="allow")

    def _check_no_duplicate_pipeline(self) -> Self:
        """Check that BIDS and PROC_PIPELINES do not have common pipelines."""

        def _check_pipeline_infos(
            pipeline_configs: list[PipelineConfig],
            pipeline_type: str,
            info_func: Callable[[PipelineConfig | BidsPipelineConfig], Tuple],
        ):
            pipeline_infos = set()
            for pipeline_config in pipeline_configs:
                pipeline_info = info_func(pipeline_config)
                if pipeline_info in pipeline_infos:
                    raise ValueError(
                        f"Found multiple configurations for {pipeline_type} pipeline: "
                        f"{pipeline_info}"
                    )
                pipeline_infos.add(pipeline_info)
            return pipeline_infos

        _check_pipeline_infos(
            self.PROC_PIPELINES,
            pipeline_type="processing",
            info_func=lambda x: (x.NAME, x.VERSION),
        )
        _check_pipeline_infos(
            self.BIDS_PIPELINES,
            pipeline_type="BIDS conversion",
            info_func=lambda x: (x.NAME, x.VERSION, x.STEP),
        )

    def _propagate_container_config(self) -> Self:
        """Propagate the container config to all pipelines."""

        def _propagate(pipeline_configs: list[PipelineConfig]):
            for pipeline_config in pipeline_configs:
                container_config = pipeline_config.get_container_config()
                if container_config.INHERIT:
                    container_config.merge_args_and_env_vars(self.CONTAINER_CONFIG)

        _propagate(self.BIDS_PIPELINES)
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
        for pipeline_config in self.PROC_PIPELINES:
            if (
                pipeline_config.NAME == pipeline_name
                and pipeline_config.VERSION == pipeline_version
            ):
                return pipeline_config

        raise ValueError(
            "No config found for pipeline with "
            f"NAME={pipeline_name}, "
            f"VERSION={pipeline_version}"
        )

    def get_bids_pipeline_config(
        self, pipeline_name: str, pipeline_version: str, pipeline_step: str
    ) -> BidsPipelineConfig:
        """Get the config for a BIDS pipeline."""
        for pipeline_config in self.BIDS_PIPELINES:
            if (
                pipeline_config.NAME == pipeline_name
                and pipeline_config.VERSION == pipeline_version
                and pipeline_config.STEP == pipeline_step
            ):
                return pipeline_config

        raise ValueError(
            "No config found for BIDS pipeline with "
            f"NAME={pipeline_name}, "
            f"VERSION={pipeline_version}, "
            f"STEP={pipeline_step}"
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
    def load(cls, path: str | Path, apply_globals_replacement=True) -> Self:
        """Load a dataset configuration."""
        config = cls(**load_json(path))

        if apply_globals_replacement:
            config_text = config.model_dump_json()
            for key, value in config.GLOBALS.items():
                config_text = config_text.replace(key, value)
                config = cls(**json.loads(config_text))

        return config
