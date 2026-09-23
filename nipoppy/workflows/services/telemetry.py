"""Telemetry handler for Nipoppy."""

from __future__ import annotations

# Shutdown pattern reference:
# https://oneuptime.com/blog/post/2026-02-06-otel-sdk-shutdown-python-atexit-sigterm/view
import atexit
import os
import signal
import sys
import threading
from dataclasses import dataclass

import httpx
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Counter, NoOpMeter
from opentelemetry.sdk.metrics import Counter as SDKCounter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

from nipoppy.env import (
    PROGRAM_NAME,
    PROGRAM_VERSION,
    TELEMETRY_DEFAULT_OTLP_ENDPOINT,
    TELEMETRY_EXPORT_TIMEOUT_SECONDS,
    TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS,
)
from nipoppy.exceptions import ReturnCode
from nipoppy.logger import get_logger

logger = get_logger()

_GEOIP_TIMEOUT = 1


def _get_user_country(timeout: float = 1) -> str:
    """
    Get the user's country code from their public IP address.

    Returns a two-letter ISO country code (e.g. "US", "CA", "IN").
    """
    response = httpx.get("https://api.db-ip.com/v2/free/self", timeout=timeout)

    response.raise_for_status()
    data = response.json()

    country_code = data.get("countryCode")
    return country_code.upper()


@dataclass
class MetricInstruments:
    """OpenTelemetry counter instruments."""

    # Command outcomes (attributes: command, status, return_code)
    commands_completed: Counter
    # Geographic distribution (attributes: country, e.g. US, CA, IN)
    location_by_country: Counter


class TelemetryHandler:
    """Self-contained OpenTelemetry metrics handler."""

    def __init__(
        self,
        service_name: str = PROGRAM_NAME,
        service_version: str | None = PROGRAM_VERSION,
        otlp_endpoint: str | None = None,
        export_interval_millis: int = TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS,
        metric_reader: MetricReader | None = None,
    ) -> None:
        """Create a telemetry handler.

        Parameters
        ----------
        service_name : str
            Service name for metrics (default: `nipoppy.env.PROGRAM_NAME`).
        service_version : str, optional
            Version tag (default: `nipoppy.env.PROGRAM_VERSION`).
        otlp_endpoint : str, optional
            Collector endpoint (default:
            `nipoppy.env.TELEMETRY_DEFAULT_OTLP_ENDPOINT`).
        export_interval_millis : int
            Export frequency in milliseconds, capped at
            `nipoppy.env.TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS`
            (default: `TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS`).
        metric_reader : opentelemetry MetricReader, optional
            Pre-built reader to use instead of the default OTLP/HTTP exporter.
            Primarily for testing (e.g. InMemoryMetricReader).
        """
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint
        self.export_interval_millis = export_interval_millis
        self.metric_reader = metric_reader

        self.provider: MeterProvider | None = None
        self.metrics: MetricInstruments | None = None
        self._initialized = False
        self.shutdown_called = False
        self._location_thread: threading.Thread | None = None

    @property
    def is_initialized(self) -> bool:
        """True if telemetry is initialized and active."""
        return self._initialized

    def initialize(self) -> bool:
        """
        Initialize the meter provider and metric instruments.

        Safe to call multiple times (only initializes once). Returns False if
        initialization is disabled or fails.
        """
        if self.is_initialized:
            return True
        if self.shutdown_called:
            return False

        original_sigterm = signal.getsignal(signal.SIGTERM)

        def _sigterm_handler(signum, frame):
            self.shutdown()
            if callable(original_sigterm):
                original_sigterm(signum, frame)
            else:
                sys.exit(0)

        try:
            resource = Resource(
                attributes={
                    SERVICE_NAME: self.service_name,
                    SERVICE_VERSION: self.service_version or "unknown",
                }
            )

            reader = self.metric_reader or self.build_default_reader()

            self.provider = MeterProvider(
                resource=resource,
                metric_readers=[reader],
                shutdown_on_exit=False,
            )
            meter = self.provider.get_meter(__name__)
            if isinstance(meter, NoOpMeter):
                self.provider = None
                return False
            self.metrics = self.create_metric_instruments(meter)

            # Flush and export pending metrics on normal exit and Ctrl+C (SIGINT
            # raises KeyboardInterrupt, which unwinds normally). atexit does not
            # fire on SIGTERM, so that signal gets its own handler below.
            atexit.register(self.shutdown)
            signal.signal(signal.SIGTERM, _sigterm_handler)
            self._initialized = True

            return True

        except Exception as e:
            if self.provider is not None:
                self.provider.shutdown()
            self.provider = None
            self.metrics = None
            self._initialized = False
            logger.debug(
                f"Telemetry initialization failed: {e}. Continuing without telemetry."
            )
            return False

    def build_default_reader(self) -> MetricReader:
        """Build the default OTLP/HTTP exporting reader."""
        otlp_endpoint = self.otlp_endpoint
        if otlp_endpoint is None:
            otlp_endpoint = os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                TELEMETRY_DEFAULT_OTLP_ENDPOINT,
            )

        # OTLP/HTTP keeps the scheme in the URL (https:// implies TLS). When an
        # endpoint is passed explicitly the SDK does not append the signal path,
        # so add /v1/metrics here if the user gave only a base endpoint.
        if not otlp_endpoint.rstrip("/").endswith("/v1/metrics"):
            otlp_endpoint = otlp_endpoint.rstrip("/") + "/v1/metrics"

        # Short timeout so an unreachable collector cannot stall shutdown, which
        # runs at exit. The exporter otherwise defaults to 10 seconds.
        otlp_exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint,
            timeout=TELEMETRY_EXPORT_TIMEOUT_SECONDS,
            preferred_temporality={SDKCounter: AggregationTemporality.DELTA},
        )

        # Short export interval so the HTTP session is established before shutdown.
        return PeriodicExportingMetricReader(
            otlp_exporter,
            export_interval_millis=min(
                self.export_interval_millis, TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS
            ),
        )

    def create_metric_instruments(self, meter) -> MetricInstruments:
        """Create metric instruments."""
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

    def record_command_completion(
        self, command_name: str, return_code: ReturnCode
    ) -> None:
        """Emit a commands_completed metric."""
        try:
            if not self.is_initialized:
                return
            self.metrics.commands_completed.add(
                1,
                attributes={
                    "command": command_name,
                    "status": return_code.name,
                    "return_code": str(return_code.value),
                },
            )
        except Exception as e:
            logger.debug(f"Failed to record command completion: {e}")

    def record_location_async(self) -> None:
        """Look up the country in a background thread and record the metric."""
        if not self.is_initialized:
            return

        def _worker() -> None:
            try:
                country_code = _get_user_country(timeout=_GEOIP_TIMEOUT)
                self.metrics.location_by_country.add(
                    1,
                    attributes={"country": country_code},
                )
            except Exception as e:
                logger.debug(f"Country lookup failed: {e}")

        self._location_thread = threading.Thread(
            target=_worker, daemon=True, name=f"{PROGRAM_NAME}-geoip"
        )
        self._location_thread.start()

    def shutdown(self) -> None:
        """Flush and shut down the meter provider."""
        if self.shutdown_called:
            return
        self.shutdown_called = True
        if self._location_thread is not None:
            self._location_thread.join(timeout=2 * _GEOIP_TIMEOUT)
        if self.provider is not None:
            self.provider.shutdown()
        self.provider = None
        self.metrics = None
        self._initialized = False


_telemetry_handler: TelemetryHandler | None = None


def get_telemetry_handler() -> TelemetryHandler:
    """Return the process-wide initialized telemetry handler.

    The handler is created once per process and shared by all callers, so there is
    a single meter provider, `atexit` registration and SIGTERM handler. Both the
    creation and `initialize()` are idempotent, so repeated calls are cheap.
    """
    global _telemetry_handler

    if _telemetry_handler is None:
        _telemetry_handler = TelemetryHandler()

    _telemetry_handler.initialize()
    return _telemetry_handler
