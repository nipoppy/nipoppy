"""Variable Definitions."""

import os
from enum import Enum
from typing import TypeVar

StrOrPathLike = TypeVar("StrOrPathLike", str, os.PathLike)

PROGRAM_NAME = "nipoppy"
NIPOPPY_DIR_NAME = ".nipoppy"
ZENODO_COMMUNITY_ID = "1c136bd0-655e-495f-8460-884751d4fdf4"


class CURRENT_SCHEMA_VERSION(str, Enum):
    """Current schema versions for Nipoppy configuration files."""

    STUDY = "1"
    PIPELINE = "1"
    TRACKER = "1"
    LAYOUT = "1"


# BIDS
BIDS_SUBJECT_PREFIX = "sub-"
BIDS_SESSION_PREFIX = "ses-"
FAKE_SESSION_ID = "unnamed"

# default config
DEFAULT_PIPELINE_STEP_NAME = "default"

# file extensions
EXT_TAR = ".tar"
EXT_LOG = ".log"


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
