"""File operations utility functions."""

import shutil
from pathlib import Path

from nipoppy.exceptions import FileOperationError
from nipoppy.logger import get_logger

logger = get_logger()

# TODO: Implement a dry-run decorator to avoid repeating dry_run checks


def mkdir(dpath: Path, dry_run=False):
    """Create a directory (including parents).

    Do nothing if the directory already exists.
    """
    if dpath.is_dir():
        return  # Directory already exists

    if dpath.exists():
        raise FileOperationError(f"Path already exists and is not a directory: {dpath}")

    logger.debug(f"Creating directory {dpath}")
    if not dry_run:
        dpath.mkdir(parents=True, exist_ok=True)


def copy(source: Path, target: Path, dry_run=False, exist_ok: bool = False):
    """
    Copy a file or directory.

    Raise an error by default if the target path already exists.
    """
    if target.exists() and not exist_ok:
        raise FileOperationError(f"Target already exists: {target}")

    logger.debug(f"Copying {source} to {target}")
    if not dry_run:
        if source.is_file():
            shutil.copy2(src=source, dst=target)
        else:
            shutil.copytree(src=source, dst=target, dirs_exist_ok=exist_ok)


def movetree(source: Path, target: Path, dry_run=False):
    """Move directory tree."""
    logger.debug(f"Moving {source} to {target}")
    if not dry_run:
        mkdir(target)
        for file_path in source.iterdir():
            shutil.move(src=file_path, dst=target)
        source.rmdir()


def symlink(source: Path, target: Path, dry_run=False):
    """Create a symlink: target -> source."""
    logger.debug(f"Creating a symlink from {source} to {target}")
    if not dry_run:
        target.symlink_to(source)


def rm(path: Path, dry_run=False):
    """Remove a file, directory, or symlink."""
    logger.debug(f"Removing {path}")
    if not dry_run:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
