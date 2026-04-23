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
    default_hint = ""

    def __init__(self, message: str = "", hint: str | None = None):
        self.message = message
        self.hint = hint
        super().__init__(self.message)

    def __str__(self):
        return self.message

    @property
    def troubleshooting_hint(self) -> str:
        """Return the troubleshooting hint attached to this error."""
        return self.hint or self.default_hint


###########
# Generic #
###########
class ConfigError(NipoppyError, ValueError):
    """Exception raised for invalid configuration values."""

    code = ReturnCode.INVALID_CONFIG
    default_hint = (
        "Review your configuration files and CLI options for missing fields, "
        "invalid values, or type mismatches."
    )


class TerminatedByUserError(NipoppyError):
    """Exception raised when the process is terminated by the user (e.g., Ctrl-C)."""

    code = ReturnCode.TERMINATED


class FileOperationError(NipoppyError, IOError):
    """Exception raised for file system operations that fail."""

    default_hint = (
        "Confirm all input/output paths exist and you have the required file "
        "permissions."
    )


class WorkflowError(NipoppyError, RuntimeError):
    """Base exception class for workflow-related errors."""

    code = ReturnCode.WORKFLOW_FAILURE
    default_hint = (
        "Check the workflow arguments and dataset state, then rerun the command "
        "with --verbose for additional context."
    )


####################
# Module specific #
###################
class ContainerError(NipoppyError):
    """Exception for container-related errors."""

    code = ReturnCode.CONTAINER_ERROR
    default_hint = (
        "Verify the container engine is installed and running, and confirm image "
        "paths or URIs are valid."
    )


class ExecutionError(NipoppyError, RuntimeError):
    """Exception for pipeline execution errors."""

    code = ReturnCode.PIPELINE_EXECUTION_ERROR
    default_hint = (
        "Inspect the pipeline logs to locate the failed step, then rerun after "
        "fixing the reported command or input."
    )


class LayoutError(NipoppyError, ValueError):
    """Exception for layout validation errors."""

    code = ReturnCode.INVALID_LAYOUT
    default_hint = (
        "Check the dataset structure and required Nipoppy layout files, then "
        "rerun the command."
    )


class TabularError(NipoppyError):
    """Base exception class for tabular-related errors."""

    code = ReturnCode.INVALID_TABULAR_DATA
    default_hint = (
        "Verify your tabular files include expected columns and valid values, and "
        "fix formatting issues before rerunning."
    )
