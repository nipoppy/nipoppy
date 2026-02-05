"""
CLIENT-SIDE: Metric definitions and OpenTelemetry setup

This module handles:
- Setting up OpenTelemetry meter provider
- Creating metric instruments (two separate metrics for separation of concerns)
- Providing thread-safe access to metrics
"""

import os
from typing import Optional, Dict

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION


# === PRESENTATION MARKER: Global State ===
# Module-level state (initialized once)
_METER: Optional[metrics.Meter] = None
_METRICS: Optional[Dict] = None


def initialize_telemetry(
    service_name: str = "nipoppy",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    export_interval_millis: int = 1000,  # DEMO: 1s | PRODUCTION: 10000 (10s)
) -> bool:
    """
    CLIENT-SIDE: Initialize OpenTelemetry metrics

    Sets up meter provider, creates metric instruments.
    Safe to call multiple times (only initializes once).
    Fail-safe: Returns False if initialization fails, never crashes.

    Args:
        service_name: Service name for metrics (default: "nipoppy")
        service_version: Version tag (default: "1.0.0")
        otlp_endpoint: Collector endpoint (default: localhost:4317)
        export_interval_millis: Export frequency (demo: 1s, prod: 10s)

    Returns:
        True if initialized successfully, False otherwise
    """
    global _METER, _METRICS

    # Already initialized
    if _METER is not None:
        return True

    # Check if disabled via environment variable
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return False

    try:
        # === PRESENTATION MARKER: OTLP Endpoint Configuration ===
        if otlp_endpoint is None:
            otlp_endpoint = os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                "http://localhost:4317"
            )

        # Strip http:// or https:// prefix for gRPC
        if otlp_endpoint.startswith("http://"):
            otlp_endpoint = otlp_endpoint.replace("http://", "")
        elif otlp_endpoint.startswith("https://"):
            otlp_endpoint = otlp_endpoint.replace("https://", "")

        # === PRESENTATION MARKER: Resource Attributes ===
        # Metadata attached to all metrics from this service
        resource = Resource(
            attributes={
                SERVICE_NAME: service_name,
                SERVICE_VERSION: service_version,
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            }
        )

        # === PRESENTATION MARKER: OTLP Exporter (CLIENT sends to SERVER) ===
        otlp_exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # For local demo (use TLS in production)
        )

        # === PRESENTATION MARKER: Export Interval ===
        # DEMO: 1 second for live presentations
        # PRODUCTION: 10 seconds to reduce overhead
        metric_reader = PeriodicExportingMetricReader(
            otlp_exporter,
            export_interval_millis=export_interval_millis,
        )

        # Create provider and set as global
        provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
        metrics.set_meter_provider(provider)

        # Create meter
        _METER = metrics.get_meter(__name__)

        # === PRESENTATION MARKER: Create Metric Instruments ===
        _METRICS = _create_metric_instruments(_METER)

        print(f"✓ Telemetry enabled → {otlp_endpoint}")
        return True

    except Exception as e:
        print(f"⚠ Warning: Telemetry initialization failed: {e}")
        print("  Continuing without telemetry...")
        return False


def _create_metric_instruments(meter: metrics.Meter) -> Dict:
    """
    CLIENT-SIDE: Create Nipoppy metric instruments

    Two metrics for separation of concerns:
    1. Command tracking (core) - which commands are used
    2. Location tracking (additional) - geographic distribution

    Args:
        meter: Meter instance from OpenTelemetry

    Returns:
        Dictionary of metric instruments
    """
    return {
        # === METRIC 1: Command Tracking (CORE FEATURE) ===
        # Purpose: Track which commands are executed and how often
        # Attributes: command (init, reorg, bidsify, process, etc.)
        "commands_executed": meter.create_counter(
            name="nipoppy.commands.executed",
            description="Number of Nipoppy commands executed",
            unit="commands",
        ),

        # === METRIC 2: Command Completion Status ===
        # Purpose: Track command outcomes (success, partial, failure)
        # Attributes: command, status, return_code
        "commands_completed": meter.create_counter(
            name="nipoppy.commands.completed",
            description="Number of Nipoppy commands completed with status",
            unit="commands",
        ),

        # === METRIC 3: Location Tracking (ADDITIONAL FEATURE) ===
        # Purpose: Track geographic distribution of installations
        # Attributes: country (US, CA, IN, etc.)
        # Note: Using UpDownCounter as gauge-like metric for current state
        "location_by_country": meter.create_up_down_counter(
            name="nipoppy.location.by_country",
            description="Number of active installations per country",
            unit="installations",
        ),
    }


def get_metrics() -> Optional[Dict]:
    """
    CLIENT-SIDE: Get metric instruments (thread-safe)

    Returns:
        Dictionary of metric instruments, or None if not initialized
    """
    return _METRICS


def is_telemetry_enabled() -> bool:
    """
    Check if telemetry is enabled and initialized

    Returns:
        True if telemetry is active, False otherwise
    """
    return _METRICS is not None
