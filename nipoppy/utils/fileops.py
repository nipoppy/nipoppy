"""File operations utility functions."""

import logging
import os
import os.path
import shutil
from pathlib import Path

from nipoppy.exceptions import FileOperationError
from nipoppy.logger import get_logger

logger = get_logger()

# TODO: Implement a dry-run decorator to avoid repeating DRY_RUN checks


def mkdir(dpath: Path, DRY_RUN=False, **kwargs):
    """
    Create a directory (by default including parents).

    Do nothing if the directory already exists.
    """
    kwargs_to_use = {"parents": True, "exist_ok": True}
    kwargs_to_use.update(kwargs)

    dpath = Path(dpath)

    if not dpath.exists():
        logger.debug(f"Creating directory {dpath}")
        if not DRY_RUN:
            dpath.mkdir(**kwargs_to_use)
    elif not dpath.is_dir():
        raise FileOperationError(f"Path already exists but is not a directory: {dpath}")


def copy(path_source: Path, path_dest: Path, DRY_RUN=False, **kwargs):
    """Copy a file or directory."""
    logger.debug(f"Copying {path_source} to {path_dest}")
    if not DRY_RUN:
        shutil.copy2(src=path_source, dst=path_dest, **kwargs)


def copytree(path_source: Path, path_dest: Path, DRY_RUN=False, **kwargs):
    """Copy directory tree."""
    logger.debug(f"Copying {path_source} to {path_dest}")
    if not DRY_RUN:
        shutil.copytree(src=path_source, dst=path_dest, **kwargs)


def movetree(
    path_source: Path,
    path_dest: Path,
    DRY_RUN=False,
    kwargs_mkdir=None,
    kwargs_move=None,
):
    """Move directory tree."""
    kwargs_mkdir = kwargs_mkdir or {}
    kwargs_move = kwargs_move or {}
    logger.debug(f"Moving {path_source} to {path_dest}")
    if not DRY_RUN:
        mkdir(path_dest, **kwargs_mkdir)
        file_names = os.listdir(path_source)
        for file_name in file_names:
            shutil.move(
                src=os.path.join(path_source, file_name),  # Path.joinpath()
                dst=path_dest,
                **kwargs_move,
            )
        Path(path_source).rmdir()


def create_symlink(path_source: Path, path_dest: Path, DRY_RUN=False, **kwargs):
    """Create a symlink to another path."""
    logger.debug(f"Creating a symlink from {path_source} to {path_dest}")
    if not DRY_RUN:
        os.symlink(path_source, path_dest, **kwargs)  # Path.symlink_to()


def rm(path: Path, DRY_RUN=False, **kwargs):
    """Remove a file or directory."""
    kwargs_to_use = {"ignore_errors": True}
    kwargs_to_use.update(kwargs)
    logger.debug(f"Removing {path}")
    if not DRY_RUN:
        shutil.rmtree(path, **kwargs_to_use)


def _remove_existing(path: Path, DRY_RUN=False, log_level=logging.INFO):
    """Remove existing file, directory, or symlink without ignoring errors."""
    logger.log(level=log_level, msg=f"Removing existing {path}")
    if not DRY_RUN:
        path_obj = Path(path)
        if path_obj.is_symlink():
            path_obj.unlink()
        elif path_obj.is_dir():
            shutil.rmtree(path)
        else:
            path_obj.unlink()
