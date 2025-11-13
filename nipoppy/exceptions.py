"""Custom exception hierarchy for nipoppy."""

from enum import IntEnum


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


class NipoppyError(Exception):
    """Base exception class for all nipoppy errors."""

    code = ReturnCode.KNOWN_FAILURE

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


###########
# Generic #
###########
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


####################
# Module specific #
###################
class ContainerError(NipoppyError):
    """Exception for container-related errors."""

    code = ReturnCode.CONTAINER_ERROR


class ExecutionError(NipoppyError, RuntimeError):
    """Exception for pipeline execution errors."""

    code = ReturnCode.PIPELINE_EXECUTION_ERROR


class LayoutError(NipoppyError, ValueError):
    """Exception for layout validation errors."""

    code = ReturnCode.INVALID_LAYOUT


class TabularError(NipoppyError):
    """Base exception class for tabular-related errors."""

    code = ReturnCode.INVALID_TABULAR_DATA
