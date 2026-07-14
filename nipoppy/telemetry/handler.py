"""
Telemetry handler for Nipoppy.

Consolidates OpenTelemetry setup, metric instruments, command-completion
tracking and geographic (country) tracking into a single class.

Telemetry is non-confounding by design: every public method is fail-safe and
never raises, so a broken or unreachable telemetry backend can never disrupt
the CLI.
"""

from __future__ import annotations

# Shutdown pattern reference:
# https://oneuptime.com/blog/post/2026-02-06-otel-sdk-shutdown-python-atexit-sigterm/view
import atexit
import logging
import os
import signal
import sys
from dataclasses import dataclass

import httpx
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Counter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

from nipoppy.exceptions import ReturnCode
from nipoppy.logger import get_logger

logger = get_logger()


def get_user_country() -> str:
    """
    Get the user's country code from their public IP address.

    Returns a two-letter ISO country code (e.g. "US", "CA", "IN") or
    "UNKNOWN" on any failure.
    """
    try:
        ip_response = httpx.get("https://api.ipify.org", timeout=5)
        ip_response.raise_for_status()
        public_ip = ip_response.text.strip()

        response = httpx.get(f"https://api.db-ip.com/v2/free/{public_ip}", timeout=5)
        response.raise_for_status()
        data = response.json()

        country_code = data.get("countryCode")
        if country_code and isinstance(country_code, str) and len(country_code) == 2:
            return country_code.upper()

        return "UNKNOWN"

    except Exception as e:
        # Debug-level only: telemetry stays invisible in normal runs.
        logger.debug(f"GeoIP country lookup failed: {e}")
        return "UNKNOWN"


@dataclass
class MetricInstruments:
    """OpenTelemetry counter instruments used by Nipoppy telemetry."""

    # Command outcomes (attributes: command, status, return_code)
    commands_completed: Counter
    # Geographic distribution (attributes: country, e.g. US, CA, IN)
    location_by_country: Counter


class TelemetryHandler:
    """
    Self-contained OpenTelemetry metrics handler.

    Each instance owns its own MeterProvider, so it does not touch the global
    OpenTelemetry state and multiple instances can coexist safely. All public
    methods are fail-safe and never raise.
    """

    def __init__(
        self,
        service_name: str = "nipoppy",
        service_version: str = "1.0.0",
        otlp_endpoint: str | None = None,
        export_interval_millis: int = 10000,
        metric_reader: MetricReader | None = None,
    ) -> None:
        """Create a telemetry handler (does not initialize OpenTelemetry yet).

        Parameters
        ----------
        service_name : str
            Service name for metrics (default: "nipoppy").
        service_version : str
            Version tag (default: "1.0.0").
        otlp_endpoint : str, optional
            Collector endpoint (default: https://telemetry.nipoppy.org).
        export_interval_millis : int
            Export frequency in milliseconds (default: 10000).
        metric_reader : opentelemetry MetricReader, optional
            Pre-built reader to use instead of the default OTLP/HTTP exporter.
            Primarily for testing (e.g. InMemoryMetricReader).
        """
        self._service_name = service_name
        self._service_version = service_version
        self._otlp_endpoint = otlp_endpoint
        self._export_interval_millis = export_interval_millis
        self._metric_reader = metric_reader

        self._provider: MeterProvider | None = None
        self._metrics: MetricInstruments | None = None
        self._shutdown_called = False

    @property
    def is_enabled(self) -> bool:
        """True if telemetry is initialized and active."""
        return self._metrics is not None

    def initialize(self) -> bool:
        """
        Initialize the meter provider and metric instruments.

        Safe to call multiple times (only initializes once). Returns False if
        initialization is disabled or fails; never raises.
        """
        if self._provider is not None:
            return True

        if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
            return False

        try:
            # Telemetry must never disrupt the CLI. The OTLP/HTTP exporter logs a
            # full traceback when the collector is unreachable; silence OTel's own
            # logging so export failures stay invisible to the user.
            logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)

            resource = Resource(
                attributes={
                    SERVICE_NAME: self._service_name,
                    SERVICE_VERSION: self._service_version,
                    "deployment.environment": os.getenv("ENVIRONMENT", "development"),
                }
            )

            reader = self._metric_reader or self._build_default_reader()

            self._provider = MeterProvider(
                resource=resource,
                metric_readers=[reader],
            )
            meter = self._provider.get_meter(__name__)
            self._metrics = self._create_metric_instruments(meter)

            # Flush and export pending metrics on exit (normal exit, Ctrl+C, SIGTERM).
            atexit.register(self.shutdown)

            original_sigterm = signal.getsignal(signal.SIGTERM)

            def _sigterm_handler(signum, frame):
                self.shutdown()
                if callable(original_sigterm):
                    original_sigterm(signum, frame)
                else:
                    sys.exit(0)

            signal.signal(signal.SIGTERM, _sigterm_handler)

            return True

        except Exception as e:
            # Fail silently: telemetry issues must never surface to the user.
            logger.debug(
                f"Telemetry initialization failed: {e}. Continuing without telemetry."
            )
            return False

    def _build_default_reader(self) -> MetricReader:
        """Build the default OTLP/HTTP exporting reader."""
        otlp_endpoint = self._otlp_endpoint
        if otlp_endpoint is None:
            otlp_endpoint = os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                "https://telemetry.nipoppy.org",
            )

        # OTLP/HTTP keeps the scheme in the URL (https:// implies TLS). When an
        # endpoint is passed explicitly the SDK does not append the signal path,
        # so add /v1/metrics here if the user gave only a base endpoint.
        if not otlp_endpoint.rstrip("/").endswith("/v1/metrics"):
            otlp_endpoint = otlp_endpoint.rstrip("/") + "/v1/metrics"

        # Force DELTA temporality so the collector's deltatocumulative processor
        # can accumulate across short-lived process runs. Without this the
        # OTLPMetricExporter defaults to CUMULATIVE, sending value=1 every time.
        os.environ["OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"] = "delta"
        otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)

        # Short export interval so the HTTP session is established before shutdown.
        # For CLI tools the periodic export rarely fires, but the shutdown flush
        # reuses the already-open connection — making export reliable even for
        # 2s commands.
        return PeriodicExportingMetricReader(
            otlp_exporter,
            export_interval_millis=min(self._export_interval_millis, 2000),
        )

    def _create_metric_instruments(self, meter) -> MetricInstruments:
        """Create Nipoppy metric instruments."""
        return MetricInstruments(
            commands_completed=meter.create_counter(
                name="commands.completed",
                description="Number of Nipoppy commands completed with status",
                unit="commands",
            ),
            location_by_country=meter.create_counter(
                name="location.by_country",
                description="Number of installations per country",
                unit="installations",
            ),
        )

    def record_command_completion(self, command_name: str, return_code: int) -> None:
        """Emit a commands_completed metric. Fail-safe — never raises."""
        try:
            if self._metrics is None:
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
            self._metrics.commands_completed.add(
                1,
                attributes={
                    "command": command_name,
                    "status": status,
                    "return_code": str(int(return_code)),
                },
            )
        except Exception:
            pass

    def record_location(self) -> None:
        """
        Perform a GeoIP lookup and record the country metric. Fail-safe.

        Called once during `nipoppy init`.
        """
        try:
            if self._metrics is None:
                return
            country_code = get_user_country()
            self._metrics.location_by_country.add(
                1,
                attributes={"country": country_code},
            )
        except Exception:
            pass

    def shutdown(self) -> None:
        """Flush and shut down the meter provider. Safe to call multiple times."""
        if self._shutdown_called:
            return
        self._shutdown_called = True
        if self._provider is not None:
            self._provider.shutdown()
