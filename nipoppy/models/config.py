"""Dataset configuration."""
from pathlib import Path

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
    TEMPLATEFLOW_DIR: Path = None
    SESSIONS: list[str]
    VISITS: list[str] = []
    BIDS: dict[str, WorkflowConfig]
    PROC_PIPELINES: dict[str, WorkflowConfig]
    WORKFLOW: list = []


def load_config(path: str | Path) -> Config:
    """Load a dataset configuration."""
    return Config(**load_json(path))
