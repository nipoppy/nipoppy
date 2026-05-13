"""
OpenTelemetry telemetry for Nipoppy.

Provides command completion tracking (via BaseWorkflow.run) and
geographic distribution tracking (record_location, used by init command).
"""

from nipoppy.telemetry.metrics import initialize_telemetry, is_telemetry_enabled
from nipoppy.telemetry.geo import record_location

__all__ = ["initialize_telemetry", "is_telemetry_enabled", "record_location"]
