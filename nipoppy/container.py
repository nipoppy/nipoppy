"""Classes for generating container commands."""

import argparse
import os
import platform
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Optional

from nipoppy.base import Base
from nipoppy.config.container import ContainerConfig
from nipoppy.env import ContainerCommandEnum, StrOrPathLike
from nipoppy.exceptions import ContainerError
from nipoppy.logger import get_logger

BIND_SEP = ":"

logger = get_logger()


class ContainerHandler(Base, ABC):
    """Abstract class for container handlers."""

    env_flag = "--env"

    @property
    @abstractmethod
    def command(self) -> str:
        """Container executable name."""
        pass

    @property
    @abstractmethod
    def bind_flags(self) -> tuple[str]:
        """Flag for binding paths."""
        pass

    def __init__(self, args: Iterable[str] = None):
        super().__init__()

        if args is None:
            args = []

        self.args = args[:]

    def check_command_exists(self):
        """Check that the command is available (i.e. in PATH)."""
        if not shutil.which(self.command):
            raise ContainerError(
                f"Container executable not found: {self.command}"
                ". Make sure it is installed and in your PATH."
            )

    def add_bind_arg(
        self,
        path_src: StrOrPathLike,
        path_dest: Optional[StrOrPathLike] = None,
        mode: Optional[str] = "rw",
    ):
        """Add a bind path to the container args.

        Parameters
        ----------
        path_src : nipoppy.env.StrOrPathLike
            Path on disk. If this is a relative path or contains symlinks,
            it will be resolved
        path_dest : Optional[nipoppy.env.StrOrPathLike], optional
            Path inside the container (if None, will be the same as the local path),
            by default None
        mode : str, optional
            Read/write permissions, by default "rw"
        """
        path_src = Path(path_src).resolve()
        if path_dest is None:
            path_dest = path_src

        bind_spec_components = [str(path_src)]
        bind_spec_components.append(str(path_dest))
        if mode is not None:
            bind_spec_components.append(mode)

        self.args.extend(
            [
                self.bind_flags[0],
                BIND_SEP.join(bind_spec_components),
            ]
        )

    def fix_bind_args(self):
        """Fix bind flags in args."""
        # use argparse to parse all the bind flags
        bind_spec_dest = "bind"
        parser = argparse.ArgumentParser(exit_on_error=False)
        parser.add_argument(
            *self.bind_flags, dest=bind_spec_dest, action="extend", nargs=1
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
                    bind_spec_components = bind_spec.split(BIND_SEP)
                    path_local = Path(bind_spec_components[0])
                    path_local_original = path_local

                    logger.debug(f"Checking container bind spec: {bind_spec}")

                    # path must be absolute and exist
                    path_local = path_local.resolve()
                    if path_local != path_local_original:
                        path_local = path_local.resolve()
                        logger.debug(
                            "Resolving path for container"
                            f": {path_local_original} -> {path_local}"
                        )
                    if not path_local.exists():
                        path_local.mkdir(parents=True)
                        logger.debug(
                            "Creating missing directory for container bind path"
                            f": {path_local}"
                        )

                    # replace bind spec in args
                    if path_local != path_local_original:
                        bind_spec_components[0] = str(path_local)
                        replacement_map[bind_spec] = BIND_SEP.join(bind_spec_components)

        except Exception as e:
            raise ContainerError(
                f"Error parsing {self.bind_flags} flags in container arguments: "
                f"{self.args}. Make sure each flag is followed by a valid spec (e.g. "
                f"{self.bind_flags[0]} /path/local{BIND_SEP}/path/container"
                f"{BIND_SEP}rw). Exact error was: "
                f"{type(e).__name__} {e}"
            ) from e

        # apply replacements
        args_str = shlex.join(self.args)
        for to_replace, replacement in replacement_map.items():
            args_str = args_str.replace(to_replace, replacement)

        self.args = shlex.split(args_str)

    def add_env_arg(self, key: str, value: str):
        """Set environment variables for the container."""
        self.args.extend([self.env_flag, f"{key}={value}"])

    def get_shell_command(
        self,
        subcommand: str = "run",
    ):
        """Get the shell command for running the container.

        Parameters
        ----------
        subcommand : str, optional
            Subcommand to use (e.g. "run", "exec"), by default "run"

        Returns
        -------
        str
            The command string
        """
        self.check_command_exists()
        self.fix_bind_args()
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
    def get_pull_confirmation_prompt(self, fpath_container: StrOrPathLike) -> str:
        """Get the confirmation prompt for pulling the container image.

        Parameters
        ----------
        fpath_container : nipoppy.env.StrOrPathLike
            Path where the container image will be saved

        Returns
        -------
        str
            The confirmation prompt string
        """

    @abstractmethod
    def get_pull_command(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> str:
        """Get the command to pull a container image to a specified location.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path where the container image should be saved

        Returns
        -------
        str
            The command string
        """


class ApptainerHandler(ContainerHandler):
    """Container handler for Apptainer."""

    command = "apptainer"
    bind_flags = ("--bind", "-B")

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
            raise ContainerError("Path to container image must be specified")
        return Path(fpath_container).exists()

    def get_pull_confirmation_prompt(self, fpath_container: StrOrPathLike) -> str:
        """Get the confirmation prompt for pulling the container image.

        Parameters
        ----------
        fpath_container : nipoppy.env.StrOrPathLike
            Path where the container image will be saved

        Returns
        -------
        str
            The confirmation prompt string
        """
        return (
            "This pipeline is containerized: do you want to download the "
            f"container (to [magenta]{fpath_container}[/])?"
        )

    def get_pull_command(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> str:
        """Get the command to pull a container image to a specified location.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path where the container image should be saved

        Returns
        -------
        str
            The command string
        """
        if uri is None or fpath_container is None:
            raise ContainerError(
                "Both URI and path to container image must be specified"
            )
        return shlex.join([self.command, "pull", str(fpath_container), uri])


class SingularityHandler(ApptainerHandler):
    """Container handler for Singularity."""

    command = "singularity"


class DockerHandler(ContainerHandler):
    """Container handler for Docker."""

    command = "docker"
    bind_flags = ("--volume", "-v")

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
            raise ContainerError("URI must be specified")
        uri = self._strip_prefix(uri)
        result = subprocess.run(
            [self.command, "image", "inspect", uri], capture_output=True
        )
        return result.returncode == 0

    def get_pull_confirmation_prompt(self, fpath_container: StrOrPathLike) -> str:
        """Get the confirmation prompt for pulling the container image.

        Parameters
        ----------
        fpath_container : nipoppy.env.StrOrPathLike
            Path where the container image will be saved

        Returns
        -------
        str
            The confirmation prompt string
        """
        return "This pipeline is containerized: do you want to download the container locally?"  # noqa: E501

    def get_pull_command(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> str:
        """Get the command to pull a container image to a specified location.

        Parameters
        ----------
        uri : Optional[str]
            URI of the container image (e.g. docker://...)
        fpath_container : Optional[nipoppy.env.StrOrPathLike]
            Path where the container image should be saved

        Returns
        -------
        str
            The command string
        """
        if uri is None:
            raise ContainerError("URI must be specified")
        uri = self._strip_prefix(uri)

        cmd = [self.command, "pull"]
        if platform.machine() == "amd64":
            cmd.append("--platform=linux/amd64")
        cmd.append(uri)
        return shlex.join(cmd)


class BareMetalHandler(ContainerHandler):
    """Handler for bare metal execution (no container)."""

    command = NotImplemented
    bind_flags = NotImplemented

    def add_bind_arg(
        self,
        path_src: StrOrPathLike,
        path_dest: Optional[StrOrPathLike] = None,
        mode: Optional[str] = "rw",
    ):
        """
        Add a bind path to the container args.

        Does not do anything since this is bare metal execution.
        """
        pass

    def add_env_arg(self, key: str, value: str):
        """Set environment variable."""
        os.environ[key] = value

    def is_image_downloaded(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> bool:
        """Check if a container image has been downloaded.

        Always returns True since bare metal execution does not need image.
        """
        return True

    def get_pull_confirmation_prompt(self, fpath_container: StrOrPathLike) -> str:
        """Should not be used."""  # noqa D401
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support pulling container images"
        )

    def get_pull_command(
        self, uri: Optional[str], fpath_container: Optional[StrOrPathLike]
    ) -> str:
        """Should not be used."""  # noqa D401
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support pulling container images"
        )


def get_container_handler(config: ContainerConfig) -> ContainerHandler:
    """Get a container handler for a given container config."""
    command_handler_map = {
        ContainerCommandEnum.APPTAINER: ApptainerHandler,
        ContainerCommandEnum.SINGULARITY: SingularityHandler,
        ContainerCommandEnum.DOCKER: DockerHandler,
        None: BareMetalHandler,
    }

    try:
        handler_class = command_handler_map[config.COMMAND]
    except KeyError as e:
        raise ContainerError(
            f"No container handler for command: {config.COMMAND}"
        ) from e

    handler: ContainerHandler = handler_class(args=config.ARGS)
    for bind_path in config.BIND_PATHS:
        handler.add_bind_arg(*bind_path.split(BIND_SEP))
    for key, value in config.ENV_VARS.items():
        handler.add_env_arg(key, value)

    return handler
