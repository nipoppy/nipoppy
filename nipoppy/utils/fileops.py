"""File operations utility functions."""

import errno
import shutil
import subprocess
from pathlib import Path
from tarfile import is_tarfile

from nipoppy.env import EXT_TAR
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


def _ignore_oserror_empty_dir(function, path, excinfo):
    """Ignore OSError 'Directory not empty'."""
    exception: BaseException = excinfo[1]
    if isinstance(exception, OSError) and exception.errno == errno.ENOTEMPTY:
        return
    raise exception


def tar_directory(dpath: Path, dry_run: bool = False) -> Path:
    """Create a tarball of a directory.

    The tarball is created in the same parent directory as the original directory,
    with the same name and a .tar extension.

    The original directory is NOT removed after tarring. The caller is responsible for
    removing the original directory if desired.

    Parameters
    ----------
    dpath: Path
        Path to the directory to tar.
    dry_run: bool, optional
        If True, do not actually perform the tarring operation, just log it. Default is
        False.

    Returns
    -------
    Path
        Path to the tarball.
    """
    if not dpath.exists():
        raise FileOperationError(f"Dir does not exist: {dpath}")
    if not dpath.is_dir():
        raise FileOperationError(f"Cannot tar non-directory: {dpath}")

    fpath_tarred = dpath.with_suffix(EXT_TAR)
    logger.debug(f"Tarring {dpath} to {fpath_tarred}")
    if not dry_run:
        subprocess.run(
            ["tar", "-cvf", str(fpath_tarred), "-C", str(dpath.parent), dpath.name],
            check=True,
        )
        if not (fpath_tarred.exists() and is_tarfile(fpath_tarred)):
            logger.error(f"Failed to tar {dpath} to {fpath_tarred}")

    return fpath_tarred


def rm(path: Path, dry_run=False):
    """Remove a file, directory, or symlink."""
    logger.debug(f"Removing {path}")
    if not dry_run:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path, onerror=_ignore_oserror_empty_dir)
        else:
            path.unlink()
