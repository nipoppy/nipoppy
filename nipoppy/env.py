"""Variable Definitions."""

import os
import sys
from enum import Enum
from typing import TypeVar

StrOrPathLike = TypeVar("StrOrPathLike", str, os.PathLike)

PROGRAM_NAME = "nipoppy"
NIPOPPY_DIR_NAME = ".nipoppy"

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

    SINGULARITY = "singularity"
    APPTAINER = "apptainer"


class PipelineTypeEnum(str, Enum):
    """Pipeline types."""

    BIDSIFICATION = "bidsification"
    PROCESSING = "processing"
    EXTRACTION = "extraction"


class ReturnCode:
    """Return codes used for the CLI commands."""

    SUCCESS = 0
    UNKNOWN_FAILURE = 1
    INVALID_COMMAND = 2
    PARTIAL_SUCCESS = 64
    NO_PARTICIPANTS_OR_SESSIONS_TO_RUN = 65
    MISSING_DEPENDENCY = 66


class LogColor:
    """Colors for logging."""

    SUCCESS = "green"
    PARTIAL_SUCCESS = "yellow"
    FAILURE = "red"
