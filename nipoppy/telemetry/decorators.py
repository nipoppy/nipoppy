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


def track_command(command_name: str) -> Callable:
    """
    CLIENT-SIDE: Decorator to track command execution

    Records a metric each time the command runs.
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
        2. Records command metric to telemetry
        3. Executes original command function
        4. Returns command result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # Preserves function metadata for Click
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # === PRESENTATION MARKER: Record Command Metric ===
            _record_command_metric(command_name)

            # === PRESENTATION MARKER: Execute Original Function ===
            return func(*args, **kwargs)

        return wrapper
    return decorator


def _record_command_metric(command_name: str) -> None:
    """
    CLIENT-SIDE: Internal helper to record command metric

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
