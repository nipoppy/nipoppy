"""Custom exception hierarchy for nipoppy."""

from nipoppy.env import ReturnCode


class NipoppyError(Exception):
    """Base exception class for all nipoppy errors."""

    code = ReturnCode.UNKNOWN_FAILURE

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class FileOperationError(NipoppyError, OSError):
    """Exception raised for file operation errors."""

    pass


class LayoutError(NipoppyError, ValueError):
    """Exception raised for invalid layout."""

    pass


class ConfigError(NipoppyError, ValueError):
    """Exception raised for invalid Nipoppy configuration."""

    pass


class WorkflowError(NipoppyError, RuntimeError):
    """Exception raised while launching or executing a workflow."""

    pass


class NipoppyExit(NipoppyError, SystemExit):
    """Exception to raise when exiting the program with a specific exit code."""

    def __init__(self, exit_code: int = ReturnCode.UNKNOWN_FAILURE):
        super().__init__(f"Exiting with code {exit_code}")
        self.code = exit_code
