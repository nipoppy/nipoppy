"""Variable Definitions."""

import os
from enum import Enum
from typing import TypeVar

StrOrPathLike = TypeVar("StrOrPathLike", str, os.PathLike)

PROGRAM_NAME = "nipoppy"
NIPOPPY_DIR_NAME = ".nipoppy"
ZENODO_COMMUNITY_ID = "1c136bd0-655e-495f-8460-884751d4fdf4"

BUG_REPORT_URL = (
    "https://github.com/nipoppy/nipoppy/issues/new/choose?template=1-bug.yml"
)
DISCORD_URL = "https://discord.gg/2VMKFRpjkm"

# pipeline config schema version
CURRENT_SCHEMA_VERSION = "1"

# BIDS
BIDS_SUBJECT_PREFIX = "sub-"
BIDS_SESSION_PREFIX = "ses-"
FAKE_SESSION_ID = "unnamed"

# default config
DEFAULT_PIPELINE_STEP_NAME = "default"

# user-level config
FPATH_USER_CONFIG = "~/.nipoppy/config.json"

# file extensions
EXT_TAR = ".tar"
EXT_LOG = ".log"

# dotenv files
# from highest to lowest priority
DEFAULT_DOTENV_PATHS = ("[[NIPOPPY_DPATH_ROOT]]/.env", "~/.nipoppy/.env")


class ContainerCommandEnum(str, Enum):
    """Container commands."""

    APPTAINER = "apptainer"
    DOCKER = "docker"
    SINGULARITY = "singularity"


class PipelineTypeEnum(str, Enum):
    """Pipeline types."""

    BIDSIFICATION = "bidsification"
    PROCESSING = "processing"
    EXTRACTION = "extraction"
