"""Variable Definitions."""

import os
import sys
from enum import Enum
from typing import TypeVar

StrOrPathLike = TypeVar("StrOrPathLike", str, os.PathLike)

PROGRAM_NAME = "nipoppy"
NIPOPPY_DIR_NAME = ".nipoppy"
ZENODO_COMMUNITY_ID = "1c136bd0-655e-495f-8460-884751d4fdf4"

# pipeline config schema version
CURRENT_SCHEMA_VERSION = "1"

# BIDS
BIDS_SUBJECT_PREFIX = "sub-"
BIDS_SESSION_PREFIX = "ses-"
FAKE_SESSION_ID = "unnamed"

# default config
DEFAULT_PIPELINE_STEP_NAME = "default"

# True when running tests
IS_TESTING = "pytest" in sys.modules

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


# TODO when deprecating Python 3.10, replace with StrEnum
class LogColor:
    """Colors for logging."""

    SUCCESS = "green"
    PARTIAL_SUCCESS = "yellow"
    FAILURE = "red"
