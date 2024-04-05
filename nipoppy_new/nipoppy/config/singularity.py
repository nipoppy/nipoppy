"""Singularity/Apptainer configuration model and utility functions."""

import argparse
import logging
import os
import shlex
import shutil
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from nipoppy.logger import get_logger

# singularity
SINGULARITY_BIND_FLAG = "--bind"
SINGULARITY_BIND_SEP = ":"
SINGULARITY_ENVVAR_PREFIXES = ["SINGULARITYENV_", "APPTAINERENV_"]


class SingularityConfig(BaseModel):
    """Model for Singularity/Apptainer configuration."""

    COMMAND: str = "singularity"
    SUBCOMMAND: str = "run"
    ARGS: list[str] = []
    ENV_VARS: dict[str, str] = {}
    INHERIT: bool = True

    model_config = ConfigDict(extra="forbid")

    def add_bind_path(
        self,
        path_local: str | Path,
        path_inside_container: Optional[str | Path] = None,
        mode: str = "rw",
    ):
        """Add a bind path."""
        self.ARGS = add_bind_path_to_args(
            self.ARGS,
            path_local=path_local,
            path_inside_container=path_inside_container,
            mode=mode,
        )

    def merge_args_and_env_vars(self, other: Any):
        """
        Merge arguments and environment variables with another instance.

        Arguments from other are appended to arguments of the current instance,
        but environment variables from other do not overwrite those of the current
        instance.
        """
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot merge {self.__class__} with object of type {type(other)}"
            )

        if self.ARGS != other.ARGS:
            self.ARGS.extend(other.ARGS)

        for env_var, value in other.ENV_VARS.items():
            if env_var not in self.ENV_VARS:
                self.ENV_VARS[env_var] = value

        return self


class ModelWithSingularityConfig(BaseModel):
    """Mixin for configs that have a SingularityConfig sub-config."""

    SINGULARITY_CONFIG: SingularityConfig = SingularityConfig()

    def get_singularity_config(self) -> SingularityConfig:
        """Return the pipeline's Singularity config object."""
        return self.SINGULARITY_CONFIG


def add_bind_path_to_args(
    args: list[str],
    path_local: str | Path,
    path_inside_container: Optional[str | Path] = None,
    mode: Optional[str] = "rw",
):
    """Add a bind path to the Singularity/Apptainer arguments.

    Parameters
    ----------
    args : list[str]
        Existing arguments
    path_local : str | Path
        Path on disk. If this is a relative path or contains symlinks,
        it will be resolved
    path_inside_container : Optional[str  |  Path], optional
        Path inside the container (if None, will be the same as the local path),
        by default None
    mode : str, optional
        Read/write permissions, as recognized by Singularity/Apptainer.
        Only used if path_inside_container is given, by default "rw"

    Returns
    -------
    list[str]
        The updated argument list
    """
    path_local = Path(path_local).resolve()

    bind_spec_components = [str(path_local)]
    if path_inside_container is not None:
        bind_spec_components.append(str(path_inside_container))
        if mode is not None:
            bind_spec_components.append(mode)

    args.extend(
        [
            SINGULARITY_BIND_FLAG,
            SINGULARITY_BIND_SEP.join(bind_spec_components),
        ]
    )
    return args


def check_singularity_args(
    args: list[str], logger: Optional[logging.Logger] = None
) -> list[str]:
    """Check/fix bind flags in args."""
    if logger is None:
        logger = get_logger("check_singularity_args")

    # use argparse to parse all the bind flags
    bind_spec_dest = "bind"
    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument(
        SINGULARITY_BIND_FLAG, dest=bind_spec_dest, action="extend", nargs=1
    )

    replacement_map = {}
    try:
        # get all bind arguments
        known_args, _ = parser.parse_known_args(args)
        bind_specs = getattr(known_args, bind_spec_dest)
        if bind_specs is not None:
            for bind_spec in bind_specs:
                # get the local path
                bind_spec: str
                bind_spec_components = bind_spec.split(SINGULARITY_BIND_SEP)
                path_local = Path(bind_spec_components[0])
                path_local_original = path_local

                logger.debug(f"Checking Singularity/Apptainer bind spec: {bind_spec}")

                # path must be absolute and exist
                path_local = path_local.resolve()
                if path_local != path_local_original:
                    path_local = path_local.resolve()
                    logger.warning(
                        "Resolving path for Singularity/Apptainer"
                        f": {path_local_original} -> {path_local}"
                    )
                if not path_local.exists():
                    path_local.mkdir(parents=True)
                    logger.warning(
                        "Creating missing directory for Singularity/Apptainer"
                        f" bind path: {path_local}"
                    )

                # replace bind spec in args
                if path_local != path_local_original:
                    bind_spec_components[0] = str(path_local)
                    replacement_map[bind_spec] = SINGULARITY_BIND_SEP.join(
                        bind_spec_components
                    )

    except Exception as exception:
        raise RuntimeError(
            f"Error parsing {SINGULARITY_BIND_FLAG} flags in Singularity/Apptainer"
            f" arguments: {args}. Make sure each flag is followed by a valid spec"
            f" (e.g. {SINGULARITY_BIND_FLAG} /path/local:/path/container:rw)"
            f". Exact error was: {type(exception).__name__} {exception}"
        )

    # apply replacements
    args_str = shlex.join(args)
    for to_replace, replacement in replacement_map.items():
        args_str = args_str.replace(to_replace, replacement)

    return shlex.split(args_str)


def check_singularity_command(command: str) -> str:
    """Check that the command is available (i.e. in PATH)."""
    if not shutil.which(command):
        raise RuntimeError(
            f"Singularity/Apptainer executable not found: {command}"
            ". Make sure Singularity/Apptainer is installed and in your PATH."
        )
    return command


def prepare_singularity(
    singularity_config: SingularityConfig,
    check=True,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Build the command for Singularity/Apptainer and set environment variables.

    Parameters
    ----------
    singularity_config : SingularityConfig
        Config object
    check : bool, optional
        Whether to validate config components and modify them
        if needed, by default True
    logger : Optional[logging.Logger], optional
        Logger, by default None

    Returns
    -------
    str
        The command string
    """
    command = singularity_config.COMMAND
    subcommand = singularity_config.SUBCOMMAND
    args = singularity_config.ARGS
    env_vars = singularity_config.ENV_VARS

    if check:
        command = check_singularity_command(command)
        args = check_singularity_args(args, logger=logger)

    set_singularity_env_vars(env_vars, logger=logger)

    return shlex.join([command, subcommand] + args)


def set_singularity_env_vars(
    env_vars: dict[str, str], logger: Optional[logging.Logger] = None
) -> None:
    """Set environment variables for the container."""
    if logger is None:
        logger = get_logger("set_singularity_env_vars")
    for var, value in env_vars.items():
        for prefix in SINGULARITY_ENVVAR_PREFIXES:
            var_with_prefix = f"{prefix}{var}"
            logger.info(f"Setting environment variable: {var_with_prefix}={value}")
            os.environ[var_with_prefix] = value