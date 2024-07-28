"""Variable Definitions."""

import os
from enum import Enum
from typing import TypeVar

StrOrPathLike = TypeVar("StrOrPathLike", str, os.PathLike)

# BIDS
BIDS_SUBJECT_PREFIX = "sub-"
BIDS_SESSION_PREFIX = "ses-"


# RETURN CODES
class ReturnCode(Enum):
    """Return codes used for the CLI commands."""

    SUCCESS = 0
    ERROR_RUN_SINGLE = 1


# COLORS
