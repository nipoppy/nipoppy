"""Dataset configuration."""

from pathlib import Path
from typing import Optional, Self

from pydantic import BaseModel, ConfigDict, model_validator

from nipoppy.utils import load_json

SINGULARITY_BIND_FLAG = "--bind"
SINGULARITY_BIND_SEP = ":"
SINGULARITY_ENVVAR_PREFIX = "APPTAINERENV_"


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


class PipelineConfig(BaseModel):
    """Model for workflow configuration."""

    CONTAINER: Optional[Path] = None
    URI: Optional[str] = None
    SINGULARITY_CONFIG: SingularityConfig = SingularityConfig()
    DESCRIPTOR: Optional[dict] = None
    INVOCATION: Optional[dict] = None
    PYBIDS_IGNORE: list[str] = []
    DESCRIPTION: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    def get_singularity_config(self) -> SingularityConfig:
        """Return the pipeline's Singularity config object."""
        return self.SINGULARITY_CONFIG


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
