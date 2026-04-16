"""TAR-related workflow helper."""

from pathlib import Path
from tarfile import is_tarfile
from typing import Optional

from nipoppy.env import EXT_TAR, StrOrPathLike
from nipoppy.exceptions import ConfigError, FileOperationError
from nipoppy.logger import get_logger
from nipoppy.utils import fileops
from nipoppy.workflows.base import _run_command

logger = get_logger()


class TarHandler:
    """Handle tar validation and directory archiving."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def validate_preconditions(
        self,
        tar_requested: bool,
        tracker_config_file: Optional[StrOrPathLike],
        participant_session_dir: Optional[StrOrPathLike] = None,
    ):
        """Validate TAR-related configuration requirements."""
        if not tar_requested:
            return

        if tracker_config_file is None:
            raise ConfigError(
                "Tarring requested but there is no tracker config file. "
                "Specify the TRACKER_CONFIG_FILE field for the pipeline step in "
                "the global config file, then make sure the PARTICIPANT_SESSION_DIR "
                "field is specified in the TRACKER_CONFIG_FILE file."
            )

        if participant_session_dir is None:
            raise ConfigError(
                "Tarring requested but no participant-session directory specified. "
                "The PARTICIPANT_SESSION_DIR field must be set in the tracker config "
                "file at "
                f"{tracker_config_file}"
            )

    def tar_directory(self, dpath: StrOrPathLike) -> Path:
        """Tar a directory and delete it."""
        dpath = Path(dpath)
        if not dpath.exists():
            raise FileOperationError(f"Not tarring {dpath} since it does not exist")
        if not dpath.is_dir():
            raise FileOperationError(f"Not tarring {dpath} since it is not a directory")

        tar_flags = "-cvf"
        fpath_tarred = dpath.with_suffix(EXT_TAR)

        _run_command(
            [
                "tar",
                tar_flags,
                str(fpath_tarred),
                "-C",
                str(dpath.parent),
                dpath.name,
            ],
            dry_run=self.dry_run,
        )

        if fpath_tarred.exists() and is_tarfile(fpath_tarred):
            fileops.rm(dpath, dry_run=self.dry_run)
        else:
            logger.error(f"Failed to tar {dpath} to {fpath_tarred}")

        return fpath_tarred
