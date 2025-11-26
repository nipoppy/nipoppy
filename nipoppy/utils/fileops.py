"""File operations utility functions."""

import shutil
from pathlib import Path

from nipoppy.exceptions import FileOperationError
from nipoppy.logger import get_logger

logger = get_logger()

# TODO: Implement a dry-run decorator to avoid repeating DRY_RUN checks


def mkdir(dpath: Path, DRY_RUN=False):
    """Create a directory (by default including parents).

    Do nothing if the directory already exists.
    """
    if dpath.is_dir():
        return  # Directory already exists

    if dpath.exists():
        raise FileOperationError(f"Path already exists and is not a directory: {dpath}")

    logger.debug(f"Creating directory {dpath}")
    if not DRY_RUN:
        dpath.mkdir(parents=True, exist_ok=True)


def copy(source: Path, target: Path, DRY_RUN=False, exist_ok: bool = False):
    """Copy a file or directory."""
    if target.exists() and not exist_ok:
        raise FileOperationError(f"Target already exists: {target}")

    logger.debug(f"Copying {source} to {target}")
    if not DRY_RUN:
        if source.is_file():
            shutil.copy2(src=source, dst=target)
        else:
            shutil.copytree(src=source, dst=target, dirs_exist_ok=exist_ok)


def movetree(source: Path, target: Path, DRY_RUN=False):
    """Move directory tree."""
    logger.debug(f"Moving {source} to {target}")
    if not DRY_RUN:
        mkdir(target)
        for file_path in source.iterdir():
            shutil.move(src=file_path, dst=target)
        source.rmdir()


def symlink(source: Path, target: Path, DRY_RUN=False):
    """Create a symlink to another path."""
    logger.debug(f"Creating a symlink from {source} to {target}")
    if not DRY_RUN:
        target.symlink_to(source)


def rm(path: Path, DRY_RUN=False):
    """Remove a file, directory, or symlink."""
    logger.debug(f"Removing {path}")
    if not DRY_RUN:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
