"""
CLIENT-SIDE: Decorators for command tracking

This module provides the @track_command decorator that instruments
CLI commands with telemetry while keeping the command logic clean.

Key Design: Fail-safe
- All telemetry operations wrapped in try/except
- Command ALWAYS executes, even if telemetry fails
- Silent failures - never crash user's command
"""

from functools import wraps
from typing import Callable, Any

from nipoppy.exceptions import ReturnCode


def track_command(command_name: str) -> Callable:
    """
    CLIENT-SIDE: Decorator to track command execution and completion

    Records metrics for:
    1. Command invocation (when command starts)
    2. Command completion (when command finishes, with status)

    Completely fail-safe - never crashes the command.

    Args:
        command_name: Name of command (e.g., "init", "bidsify", "process")

    Returns:
        Decorated function

    Example:
        @track_command("bidsify")
        def bidsify(**params):
            # Command logic here
            ...

    Execution Order (for presentation):
        1. Decorator intercepts function call
        2. Records command invocation metric
        3. Executes original command function
        4. Catches SystemExit to extract return code
        5. Records completion metric with status
        6. Re-raises SystemExit to preserve original behavior
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # Preserves function metadata for Click
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # === PRESENTATION MARKER: Record Command Invocation ===
            _record_command_metric(command_name)

            # === PRESENTATION MARKER: Execute and Track Completion ===
            status = "success"
            return_code = ReturnCode.SUCCESS
            try:
                return func(*args, **kwargs)
            except SystemExit as e:
                # Extract return code from SystemExit (set by exception_handler)
                return_code = e.code if isinstance(e.code, int) else ReturnCode.UNKNOWN_FAILURE
                status = _return_code_to_status(return_code)
                raise
            except Exception:
                # Fallback: exception escaped before exception_handler could convert it
                status = "failure"
                return_code = ReturnCode.UNKNOWN_FAILURE
                raise
            finally:
                _record_completion_metric(command_name, status, return_code)

        return wrapper
    return decorator


def _return_code_to_status(code: int) -> str:
    """
    Map return code to status string.

    Uses the existing ReturnCode enum values from nipoppy.exceptions.

    Args:
        code: Integer return code

    Returns:
        Status string: "success", "partial", or "failure"
    """
    if code == ReturnCode.SUCCESS:
        return "success"
    elif code in (ReturnCode.PARTIAL_SUCCESS, ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN):
        return "partial"
    else:
        return "failure"


def _record_command_metric(command_name: str) -> None:
    """
    CLIENT-SIDE: Internal helper to record command invocation metric

    Separated for easier testing and fail-safety.
    Three layers of safety:
    1. Check if metrics initialized
    2. Try-except around recording
    3. Silent failure (no exception raised)

    Args:
        command_name: Name of the command to record
    """
    from nipoppy.telemetry.metrics import get_metrics

    try:
        metrics = get_metrics()
        if metrics and "commands_executed" in metrics:
            # === PRESENTATION MARKER: Increment Counter ===
            metrics["commands_executed"].add(
                1,
                attributes={"command": command_name}
            )
    except Exception:
        # Silent failure - NEVER crash user's command
        # This is intentional for fail-safe behavior
        pass


def _record_completion_metric(command_name: str, status: str, return_code: int) -> None:
    """
    CLIENT-SIDE: Internal helper to record command completion metric

    Records the outcome of a command execution with status and return code.

    Args:
        command_name: Name of the command
        status: "success", "partial", or "failure"
        return_code: Integer return code from ReturnCode enum
    """
    from nipoppy.telemetry.metrics import get_metrics

    try:
        metrics = get_metrics()
        if metrics and "commands_completed" in metrics:
            # === PRESENTATION MARKER: Record Completion Status ===
            metrics["commands_completed"].add(
                1,
                attributes={
                    "command": command_name,
                    "status": status,
                    "return_code": str(return_code),
                }
            )
    except Exception:
        # Silent failure - NEVER crash user's command
        pass
