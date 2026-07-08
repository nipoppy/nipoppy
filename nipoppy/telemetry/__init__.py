"""
OpenTelemetry telemetry for Nipoppy.

Provides the TelemetryHandler class, which tracks command completions (via
BaseWorkflow.run) and geographic distribution (record_location, used by the
init command).
"""

from nipoppy.telemetry.handler import TelemetryHandler

__all__ = ["TelemetryHandler"]
