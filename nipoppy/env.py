"""Variable Definitions."""

import os
import sys
from typing import TypeVar

StrOrPathLike = TypeVar("StrOrPathLike", str, os.PathLike)

# BIDS
BIDS_SUBJECT_PREFIX = "sub-"
BIDS_SESSION_PREFIX = "ses-"

IS_TESTING = "pytest" in sys.modules


class ReturnCode:
    """Return codes used for the CLI commands."""

    SUCCESS = 0
    PARTIAL_SUCCESS = 1


class LogColor:
    """Colors for logging."""

    SUCCESS = "green"
    PARTIAL_SUCCESS = "yellow"
    FAILURE = "red"
