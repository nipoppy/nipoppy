"""
OpenTelemetry telemetry for Nipoppy CLI.

Two independent features:
1. Command tracking: which commands are used and how often (@track_command)
2. Location tracking: geographic distribution of installations (record_location)
"""

from nipoppy.telemetry.decorators import track_command
from nipoppy.telemetry.metrics import initialize_telemetry, is_telemetry_enabled
from nipoppy.telemetry.geo import record_location

__all__ = [
    "track_command",
    "initialize_telemetry",
    "is_telemetry_enabled",
    "record_location",
]
