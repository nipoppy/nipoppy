"""Dataset configuration."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from nipoppy.utils import load_json


class WorkflowConfig(BaseModel):
    """Model for workflow configuration."""

    VERSION: str | list[str]
    CONTAINER: Path = None


class Config(BaseModel):
    """Model for dataset configuration."""

    DATASET_NAME: str
    DATASET_ROOT: Path
    CONTAINER_STORE: Path
    SINGULARITY_PATH: str = "singularity"
    TEMPLATEFLOW_DIR: Optional[Path] = None
    SESSIONS: list[str]
    VISITS: list[str] = []
    BIDS: dict[str, WorkflowConfig]
    PROC_PIPELINES: dict[str, WorkflowConfig]
    WORKFLOW: list = []

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


def load_config(path: str | Path) -> Config:
    """Load a dataset configuration."""
    return Config(**load_json(path))
