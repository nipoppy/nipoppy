"""
Metric definitions and OpenTelemetry setup.

This module handles:
- Setting up OpenTelemetry meter provider
- Creating metric instruments
- Providing thread-safe access to metrics
"""

# Shutdown pattern reference:
# https://oneuptime.com/blog/post/2026-02-06-otel-sdk-shutdown-python-atexit-sigterm/view
import atexit
import os
import signal
import sys
from typing import Optional, Dict

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

from nipoppy.exceptions import ReturnCode


# Module-level state (initialized once)
_METER: Optional[metrics.Meter] = None
_METRICS: Optional[Dict] = None
_PROVIDER: Optional[MeterProvider] = None
_SHUTDOWN_CALLED: bool = False


def _shutdown_provider() -> None:
    """Flush and shut down the meter provider. Safe to call multiple times."""
    global _SHUTDOWN_CALLED
    if _SHUTDOWN_CALLED:
        return
    _SHUTDOWN_CALLED = True
    if _PROVIDER is not None:
        _PROVIDER.shutdown()


def initialize_telemetry(
    service_name: str = "nipoppy",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    export_interval_millis: int = 10000,
) -> bool:
    """
    Initialize OpenTelemetry metrics.

    Sets up meter provider and creates metric instruments.
    Safe to call multiple times (only initializes once).
    Returns False if initialization fails, never raises.

    Args:
        service_name: Service name for metrics (default: "nipoppy")
        service_version: Version tag (default: "1.0.0")
        otlp_endpoint: Collector endpoint (default: localhost:4317)
        export_interval_millis: Export frequency in milliseconds (default: 10000)

    Returns:
        True if initialized successfully, False otherwise
    """
    global _METER, _METRICS, _PROVIDER

    if _PROVIDER is not None:
        return True

    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return False

    try:
        if otlp_endpoint is None:
            otlp_endpoint = os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                "http://localhost:4317"
            )

        # Strip scheme prefix for gRPC; track whether to use TLS
        insecure = True
        if otlp_endpoint.startswith("https://"):
            otlp_endpoint = otlp_endpoint[len("https://"):]
            insecure = False
        elif otlp_endpoint.startswith("http://"):
            otlp_endpoint = otlp_endpoint[len("http://"):]

        resource = Resource(
            attributes={
                SERVICE_NAME: service_name,
                SERVICE_VERSION: service_version,
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            }
        )

        # Force DELTA temporality so the collector's deltatocumulative processor
        # can accumulate across short-lived process runs. Without this the
        # OTLPMetricExporter defaults to CUMULATIVE, sending value=1 every time.
        os.environ["OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"] = "delta"
        otlp_exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint,
            insecure=insecure,
        )

        # Short export interval so the gRPC connection is established before shutdown.
        # For CLI tools the periodic export rarely fires, but the shutdown flush reuses
        # the already-open connection — making export reliable even for 2s commands.
        metric_reader = PeriodicExportingMetricReader(
            otlp_exporter,
            export_interval_millis=min(export_interval_millis, 2000),
        )

        provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
        metrics.set_meter_provider(provider)

        _PROVIDER = provider
        _METER = metrics.get_meter(__name__)
        _METRICS = _create_metric_instruments(_METER)

        # Flush and export all pending metrics on exit (normal exit, Ctrl+C, or SIGTERM)
        atexit.register(_shutdown_provider)

        original_sigterm = signal.getsignal(signal.SIGTERM)

        def _sigterm_handler(signum, frame):
            _shutdown_provider()
            if callable(original_sigterm):
                original_sigterm(signum, frame)
            else:
                sys.exit(0)

        signal.signal(signal.SIGTERM, _sigterm_handler)

        return True

    except Exception as e:
        print(f"⚠ Warning: Telemetry initialization failed: {e}")
        print("  Continuing without telemetry...")
        return False


def _create_metric_instruments(meter: metrics.Meter) -> Dict:
    """
    Create Nipoppy metric instruments.

    Args:
        meter: Meter instance from OpenTelemetry

    Returns:
        Dictionary of metric instruments
    """
    return {
        # Track command outcomes (success, partial, failure)
        # Attributes: command, status, return_code
        "commands_completed": meter.create_counter(
            name="commands.completed",
            description="Number of Nipoppy commands completed with status",
            unit="commands",
        ),

        # Track geographic distribution of installations
        # Attributes: country (US, CA, IN, etc.)
        "location_by_country": meter.create_counter(
            name="location.by_country",
            description="Number of installations per country",
            unit="installations",
        ),
    }


def get_metrics() -> Optional[Dict]:
    """
    Get metric instruments.

    Returns:
        Dictionary of metric instruments, or None if not initialized
    """
    return _METRICS


def is_telemetry_enabled() -> bool:
    """
    Check if telemetry is enabled and initialized.

    Returns:
        True if telemetry is active, False otherwise
    """
    return _METRICS is not None


def record_command_completion(command_name: str, return_code: int) -> None:
    """Emit a commands_completed metric. Fail-safe — never raises."""
    try:
        metrics_dict = get_metrics()
        if metrics_dict is None:
            return
        if return_code == ReturnCode.SUCCESS:
            status = "success"
        elif return_code in (
            ReturnCode.PARTIAL_SUCCESS,
            ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN,
        ):
            status = "partial"
        else:
            status = "failure"
        metrics_dict["commands_completed"].add(
            1,
            attributes={
                "command": command_name,
                "status": status,
                "return_code": str(int(return_code)),
            },
        )
    except Exception:
        pass
