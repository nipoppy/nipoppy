"""Custom exception hierarchy for nipoppy."""

from nipoppy.env import ReturnCode


class NipoppyError(Exception):
    """Base exception class for all nipoppy errors."""

    code = ReturnCode.UNKNOWN_FAILURE

    def __init__(self, message: str = "", code: int = ReturnCode.UNKNOWN_FAILURE):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        return self.message


class ConfigError(NipoppyError, ValueError):
    """Exception raised for invalid Nipoppy configuration."""

    pass


class LayoutError(NipoppyError, ValueError):
    """Exception raised for invalid layout."""

    pass


class FileOperationError(NipoppyError, IOError):
    """Exception raised for file access errors."""

    pass


class WorkflowError(NipoppyError, RuntimeError):
    """Exception raised during a workflow execution."""

    pass
