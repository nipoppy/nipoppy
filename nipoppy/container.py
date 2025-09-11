"""Classes for generating container commands."""

import shutil
from abc import ABC, abstractmethod
from typing import Iterable


class ContainerOptionsHandler(ABC):
    """Abstract class for container options handlers."""

    bind_sep = ":"
    env_flag = "--env"

    @property
    @abstractmethod
    def command(self) -> str:
        """Container executable name."""
        pass

    @property
    @abstractmethod
    def bind_flag(self) -> str:
        """Flag for binding paths."""
        pass

    def __init__(self, args: Iterable[str] = None):
        super().__init__()
        self.args = args or []

    # methods
    def check_container_command(self) -> str:
        """Check that the command is available (i.e. in PATH)."""
        if not shutil.which(self.command):
            raise RuntimeError(
                f"Container executable not found: {self.command}"
                ". Make sure it is installed and in your PATH."
            )
        return self.command

    def add_bind_path_to_args(self):
        """Add a bind path to the container arguments."""

    def check_container_args(self):
        """Fix bind flags in args."""

    def prepare_container(self):
        """Build the command for container."""


class ApptainerOptionsHandler(ContainerOptionsHandler):
    """Container options handler for Apptainer."""

    command = "apptainer"
    bind_flag = "--bind"


class SingularityOptionsHandler(ApptainerOptionsHandler):
    """Container options handler for Singularity."""

    command = "singularity"


class DockerOptionsHandler(ContainerOptionsHandler):
    """Container options handler for Docker."""

    command = "docker"
    bind_flag = "--volume"
