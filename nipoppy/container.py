"""Classes for generating container commands."""

import argparse
import logging
import shlex
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

    def __init__(
        self, args: Iterable[str] = None, logger: Optional[logging.Logger] = None
    ):
        super().__init__()

        if logger is None:
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.INFO)

        self.args = args or []
        self.logger = logger

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
        # use argparse to parse all the bind flags
        bind_spec_dest = "bind"
        parser = argparse.ArgumentParser(exit_on_error=False)
        parser.add_argument(
            self.bind_flag, dest=bind_spec_dest, action="extend", nargs=1
        )

        replacement_map = {}
        try:
            # get all bind arguments
            known_args, _ = parser.parse_known_args(self.args)
            bind_specs = getattr(known_args, bind_spec_dest)
            if bind_specs is not None:
                for bind_spec in bind_specs:
                    # get the local path
                    bind_spec: str
                    bind_spec_components = bind_spec.split(self.bind_sep)
                    path_local = Path(bind_spec_components[0])
                    path_local_original = path_local

                    self.logger.debug(f"Checking container bind spec: {bind_spec}")

                    # path must be absolute and exist
                    path_local = path_local.resolve()
                    if path_local != path_local_original:
                        path_local = path_local.resolve()
                        self.logger.debug(
                            "Resolving path for container"
                            f": {path_local_original} -> {path_local}"
                        )
                    if not path_local.exists():
                        path_local.mkdir(parents=True)
                        self.logger.debug(
                            "Creating missing directory for container bind path"
                            f": {path_local}"
                        )

                    # replace bind spec in args
                    if path_local != path_local_original:
                        bind_spec_components[0] = str(path_local)
                        replacement_map[bind_spec] = self.bind_sep.join(
                            bind_spec_components
                        )

        except Exception as exception:
            raise RuntimeError(
                f"Error parsing {self.bind_flag} flags in container arguments: "
                f"{self.args}. Make sure each flag is followed by a valid spec (e.g. "
                f"{self.bind_flag} /path/local{self.bind_sep}/path/container"
                f"{self.bind_sep}rw). Exact error was: "
                f"{type(exception).__name__} {exception}"
            )

        # apply replacements
        args_str = shlex.join(self.args)
        for to_replace, replacement in replacement_map.items():
            args_str = args_str.replace(to_replace, replacement)

        self.args = shlex.split(args_str)

    def set_container_env_vars(self):
        """Set environment variables for the container."""

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
