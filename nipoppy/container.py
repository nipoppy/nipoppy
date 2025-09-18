"""Classes for generating container commands."""

import argparse
import logging
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Mapping, Optional

from nipoppy.base import Base
from nipoppy.config.container import ContainerConfig
from nipoppy.env import ContainerCommandEnum, StrOrPathLike


class ContainerOptionsHandler(Base, ABC):
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
        if path_inside_container is None:
            path_inside_container = path_local

        bind_spec_components = [str(path_local)]
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

    def set_container_env_vars(self, env_vars: Mapping[str, str]):
        """Set environment variables for the container."""
        for key, value in env_vars.items():
            self.args.extend([self.env_flag, f"{key}={value}"])

    def prepare_container(
        self,
        subcommand: str = "run",
    ):
        """Build the command for container.

        Parameters
        ----------
        subcommand : str, optional
            Subcommand to use (e.g. "run", "exec"), by default "run"

        Returns
        -------
        str
            The command string
        """
        self.check_container_command()
        self.check_container_args()
        return shlex.join([self.command, subcommand] + self.args)

    @abstractmethod
    def is_image_downloaded(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> bool:
        """Check if a container image has been downloaded.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path to the container image

        Returns
        -------
        bool
            True if the container image exists at the specified path
        """

    @abstractmethod
    def get_container_pull_command(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> list[str]:
        """Get the command to pull a container image to a specified location.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path where the container image should be saved

        Returns
        -------
        list[str]
            The command as a list of strings
        """


class ApptainerOptionsHandler(ContainerOptionsHandler):
    """Container options handler for Apptainer."""

    command = "apptainer"
    bind_flag = "--bind"

    def is_image_downloaded(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> bool:
        """Check if a container image has been downloaded.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...) (not used)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path to the container image

        Returns
        -------
        bool
            True if the container image exists at the specified path
        """
        if fpath_container is None:
            raise ValueError("Path to container image must be specified")
        return Path(fpath_container).exists()

    def get_container_pull_command(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> list[str]:
        """Get the command to pull a container image to a specified location.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path where the container image should be saved

        Returns
        -------
        list[str]
            The command as a list of strings
        """
        if uri is None or fpath_container is None:
            raise ValueError("Both URI and path to container image must be specified")
        return [self.command, "pull", str(fpath_container), uri]


class SingularityOptionsHandler(ApptainerOptionsHandler):
    """Container options handler for Singularity."""

    command = "singularity"


class DockerOptionsHandler(ContainerOptionsHandler):
    """Container options handler for Docker."""

    command = "docker"
    bind_flag = "--volume"

    def _strip_prefix(self, uri: str) -> str:
        return uri.removeprefix("docker://")

    def is_image_downloaded(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> bool:
        """Check if a container image has been downloaded.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path to the container image (not used)

        Returns
        -------
        bool
            True if the container image exists at the specified path
        """
        if uri is None:
            raise ValueError("URI must be specified")
        uri = self._strip_prefix(uri)
        result = subprocess.run(
            [self.command, "image", "inspect", uri], capture_output=True
        )
        return result.returncode == 0

    def get_container_pull_command(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> list[str]:
        """Get the command to pull a container image to a specified location.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path where the container image should be saved

        Returns
        -------
        list[str]
            The command as a list of strings
        """
        if uri is None:
            raise ValueError("URI must be specified")
        uri = self._strip_prefix(uri)
        return [self.command, "pull", uri]


def get_container_options_handler(
    config: ContainerConfig, logger: Optional[logging.Logger] = None
) -> ContainerOptionsHandler:
    """Get a container options handler for a given container config."""
    command_handler_map = {
        ContainerCommandEnum.APPTAINER: ApptainerOptionsHandler,
        ContainerCommandEnum.SINGULARITY: SingularityOptionsHandler,
        ContainerCommandEnum.DOCKER: DockerOptionsHandler,
    }

    try:
        handler_class = command_handler_map[config.COMMAND]
    except KeyError:
        raise ValueError(f"No container options handler for command: {config.COMMAND}")

    handler: ContainerOptionsHandler = handler_class(args=config.ARGS, logger=logger)
    handler.set_container_env_vars(config.ENV_VARS)

    return handler
