"""Classes for generating container commands."""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Optional

from nipoppy.env import StrOrPathLike


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

    def check_container_command(self) -> str:
        """Check that the command is available (i.e. in PATH)."""
        if not shutil.which(self.command):
            raise RuntimeError(
                f"Container executable not found: {self.command}"
                ". Make sure it is installed and in your PATH."
            )
        return self.command

    def add_bind_path(
        self,
        path_local: StrOrPathLike,
        path_inside_container: Optional[StrOrPathLike] = None,
        mode: Optional[str] = "rw",
    ):
        """Add a bind path to the container options.

        Parameters
        ----------
        path_local : nipoppy.env.StrOrPathLike
            Path on disk. If this is a relative path or contains symlinks,
            it will be resolved
        path_inside_container : Optional[nipoppy.env.StrOrPathLike], optional
            Path inside the container (if None, will be the same as the local path),
            by default None
        mode : str, optional
            Read/write permissions.
            Only used if path_inside_container is given, by default "rw"
        """
        path_local = Path(path_local).resolve()

        bind_spec_components = [str(path_local)]
        if path_inside_container is not None:
            bind_spec_components.append(str(path_inside_container))
            if mode is not None:
                bind_spec_components.append(mode)

        self.args.extend(
            [
                self.bind_flag,
                self.bind_sep.join(bind_spec_components),
            ]
        )

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
