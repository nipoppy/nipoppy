"""Dataset configuration."""

import os
import re
from pathlib import Path
from typing import Optional, Self, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from nipoppy.utils import load_json

SINGULARITY_BIND_FLAG = "--bind"
SINGULARITY_BIND_SEP = ":"
SINGULARITY_ENVVAR_PREFIXES = ["SINGULARITYENV_", "APPTAINERENV_"]


class BoutiquesConfig(BaseModel):
    """Model for custom configuration within a Boutiques descriptor."""

    # dpath_participant_session_result (for tarring/zipping/extracting)
    # run_on (for choosing which participants/sessions to run on)
    # bids_input (for pybids)
    pass


class SingularityConfig(BaseModel):
    """Model for Singularity/Apptainer configuration."""

    COMMAND: str = "singularity"
    SUBCOMMAND: str = "run"
    ARGS: list[str] = []
    ENV_VARS: dict[str, str] = {}

    model_config = ConfigDict(extra="forbid")

    def build_command(self) -> str:
        """Build the full Singularity command (command + subcommand + args)."""
        args = [self.COMMAND, self.SUBCOMMAND, *self.ARGS]
        return " ".join(args)

    def add_bind_path(
        self,
        path_local: str | Path,
        path_inside_container: Optional[str | Path] = None,
        mode: str = "rw",
        check_exists: bool = True,
    ):
        """Add a bind path (mount point for the container)."""
        # use absolute paths
        path_local = Path(path_local).resolve()
        if check_exists and (not path_local.exists()):
            raise FileNotFoundError(
                f"Bind path for Apptainer/Singularity does not exist: {path_local}"
            )

        if path_inside_container is None:
            path_inside_container = path_local

        self.ARGS.extend(
            [
                SINGULARITY_BIND_FLAG,
                SINGULARITY_BIND_SEP.join(
                    [
                        str(path_local),
                        str(path_inside_container),
                        mode,
                    ]
                ),
            ]
        )

    def set_env_vars(self) -> None:
        """Set environment variables for the container."""
        for key, value in self.ENV_VARS.items():
            for prefix in SINGULARITY_ENVVAR_PREFIXES:
                os.environ[f"{prefix}{key}"] = value


class PipelineConfig(BaseModel):
    """Model for workflow configuration."""

    CONTAINER: Optional[Path] = None
    URI: Optional[str] = None
    SINGULARITY_CONFIG: SingularityConfig = SingularityConfig()
    DESCRIPTOR: Optional[dict] = None
    INVOCATION: Optional[dict] = None
    PYBIDS_IGNORE: list[re.Pattern] = []
    DESCRIPTION: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    def get_singularity_config(self) -> SingularityConfig:
        """Return the pipeline's Singularity config object."""
        return self.SINGULARITY_CONFIG

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
