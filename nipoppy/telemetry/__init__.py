"""
CLIENT-SIDE: OpenTelemetry telemetry for Nipoppy CLI

This module provides minimal metrics instrumentation for tracking
command usage and geographic distribution with clear separation of concerns.

Architecture:
- decorators.py: Command tracking decorator (@track_command)
- metrics.py: Metric definitions and OpenTelemetry setup
- geo.py: Geographic location tracking (GeoIP lookup)

Two Independent Features:
1. Command Tracking (Core): Which commands are used, how often
2. Location Tracking (Additional): Geographic distribution of installations

Example Usage:
    from nipoppy.telemetry import track_command, initialize_telemetry

    # Initialize once at startup
    initialize_telemetry()

    # Decorate commands
    @track_command("bidsify")
    def bidsify(**params):
        ...
"""

from nipoppy.telemetry.decorators import track_command
from nipoppy.telemetry.metrics import initialize_telemetry, is_telemetry_enabled
from nipoppy.telemetry.geo import (
    get_user_country,
    save_country_to_config,
    record_location,
)

__all__ = [
    # Decorator (most common usage)
    "track_command",
    # Initialization
    "initialize_telemetry",
    "is_telemetry_enabled",
    # Location tracking
    "get_user_country",
    "save_country_to_config",
    "record_location",
]
