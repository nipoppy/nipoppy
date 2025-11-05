"""Variable Definitions."""

import os
import sys
from enum import Enum, IntEnum
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


class ReturnCode(IntEnum):
    """Return codes used for the CLI commands."""

    SUCCESS = 0
    FAILURE = 1  # Generic or unspecified failure
    INVALID_COMMAND = 2  # Invalid or excess argument(s)

    # 64-78: OS specified return codes
    # Reference: https://docs.python.org/3/library/os.html#os._exit

    TERMINATED = 130  # Usually used when terminated by Ctrl-C

    # 150-199: Reserved for application use
    # Reference: https://refspecs.linuxbase.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html  # noqa:E501

    # 150-159: general application return codes
    KNOWN_FAILURE = 150
    UNKNOWN_FAILURE = 151
    MISSING_DEPENDENCY = 152
    INVALID_LAYOUT = 153
    INVALID_TABULAR_DATA = 154
    INVALID_CONFIG = 155

    # 160-169: workflow-related return codes
    WORKFLOW_FAILURE = 160
    PARTIAL_SUCCESS = 161
    NO_PARTICIPANTS_OR_SESSIONS_TO_RUN = 162
    CONTAINER_ERROR = 163
    PIPELINE_EXECUTION_ERROR = 164

    # 170-199: reserved for future Nipoppy use


# TODO when deprecating Python 3.10, replace with StrEnum
class LogColor:
    """Colors for logging."""

    SUCCESS = "green"
    PARTIAL_SUCCESS = "yellow"
    FAILURE = "red"
