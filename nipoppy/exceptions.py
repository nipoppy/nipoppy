"""Custom exception hierarchy for nipoppy."""

from nipoppy.env import ReturnCode


class NipoppyError(Exception):
    """Base exception class for all nipoppy errors."""

    code = ReturnCode.KNOWN_FAILURE

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class ConfigError(NipoppyError, ValueError):
    """Exception raised for invalid configuration values."""

    code = ReturnCode.INVALID_CONFIG


class TerminatedByUserError(NipoppyError):
    """Exception raised when the process is terminated by the user (e.g., Ctrl-C)."""

    code = ReturnCode.TERMINATED


class FileOperationError(NipoppyError, IOError): ...  # noqa: D101, E701


class WorkflowError(NipoppyError, RuntimeError):
    """Base exception class for workflow-related errors."""

    code = ReturnCode.WORKFLOW_FAILURE
