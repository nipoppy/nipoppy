"""Exceptions for tabular module."""

from nipoppy.env import ReturnCode
from nipoppy.exceptions import NipoppyError


class TabularError(NipoppyError):
    """Base exception class for tabular-related errors."""

    code = ReturnCode.INVALID_TABULAR_DATA
