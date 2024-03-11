"""Dataset configuration."""

from pathlib import Path
from typing import Self

from pydantic import ConfigDict, model_validator

from nipoppy.config.pipeline import PipelineConfig
from nipoppy.config.singularity import ModelWithSingularityConfig
from nipoppy.utils import load_json


class Config(ModelWithSingularityConfig):
    """Model for dataset configuration."""

    DATASET_NAME: str
    SESSIONS: list[str]
    VISITS: list[str] = []
    BIDS: dict[str, dict[str, PipelineConfig]] = {}
    PROC_PIPELINES: dict[str, dict[str, PipelineConfig]]

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

    def _propagate_singularity_config(self) -> Self:
        """Propagate the Singularity config to all pipelines."""

        def _propagate(pipeline_dicts: dict[dict[PipelineConfig]]):
            for pipeline_name in pipeline_dicts:
                for pipeline_version in pipeline_dicts[pipeline_name]:
                    pipeline_config: PipelineConfig = pipeline_dicts[pipeline_name][
                        pipeline_version
                    ]
                    singularity_config = pipeline_config.get_singularity_config()
                    if singularity_config.INHERIT:
                        singularity_config.merge_args_and_env_vars(
                            self.SINGULARITY_CONFIG
                        )

        _propagate(self.BIDS)
        _propagate(self.PROC_PIPELINES)

        return self

    @model_validator(mode="after")
    def validate_and_process(self) -> Self:
        """Validate and process the configuration."""
        self._check_no_duplicate_pipeline()
        self._propagate_singularity_config()
        return self

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

    @classmethod
    def load(cls, path: str | Path) -> Self:
        """Load a dataset configuration."""
        return cls(**load_json(path))
