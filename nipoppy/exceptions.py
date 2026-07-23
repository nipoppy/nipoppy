"""Custom exception hierarchy for nipoppy."""

import json
from enum import IntEnum

from nipoppy.env import StrOrPathLike


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
        Exception.__init__(self, self.message)

    def __str__(self):
        return self.message

    @property
    def troubleshooting_hint(self) -> str:
        """Return the troubleshooting hint attached to this error."""
        return self.default_hint if self.hint is None else self.hint


class _JSONError(NipoppyError):
    """Base exception class for JSON parsing errors."""

    code = ReturnCode.UNKNOWN_FAILURE
    default_hint = "Suggested fix: Check the JSON file for syntax errors, such as missing commas or mismatched brackets."  # noqa:E501


class JSONError(_JSONError, json.JSONDecodeError):
    """Exception raised for JSON parsing errors, with context about the file path."""

    def __init__(
        self,
        e: json.JSONDecodeError,
        *,
        fpath: StrOrPathLike,
        hint: str | None = None,
    ):
        e.msg += f": {fpath}"
        json.JSONDecodeError.__init__(self, e.msg, e.doc, e.pos)

        # self.args[0] is the JSONDecodeError error message
        _JSONError.__init__(self, self.args[0], hint=hint)


class JSON5Error(_JSONError, ValueError):
    """Exception raised for JSON5 parsing errors, with context about the file path."""

    def __init__(
        self,
        e: ValueError,
        *,
        fpath: StrOrPathLike,
        hint: str | None = None,
    ):
        msg = f"{str(e)}: {fpath}"

        # self.args[0] is the JSONDecodeError error message
        _JSONError.__init__(self, msg, hint=hint)


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

    default_hint = "Confirm all input/output paths are correct."


class WorkflowError(NipoppyError, RuntimeError):
    """Base exception class for workflow-related errors."""

    code = ReturnCode.WORKFLOW_FAILURE
    default_hint = "Rerun with --verbose for additional context."


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
    default_hint = "Inspect the pipeline logs to locate the failed step"


class LayoutError(NipoppyError, ValueError):
    """Exception for layout validation errors."""

    code = ReturnCode.INVALID_LAYOUT
    default_hint = "Make sure this command is being run on a valid Nipoppy study."


class TabularError(NipoppyError):
    """Base exception class for tabular-related errors."""

    code = ReturnCode.INVALID_TABULAR_DATA
    default_hint = (
        "Verify your tabular files include expected columns and valid values, and "
        "fix formatting issues before rerunning."
    )
