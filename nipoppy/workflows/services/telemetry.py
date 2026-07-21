"""Telemetry handler for Nipoppy."""

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

from nipoppy.env import PROGRAM_NAME, TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS
from nipoppy.exceptions import ReturnCode
from nipoppy.logger import get_logger

logger = get_logger()


def _get_user_country(timeout: float = 5) -> str:
    """
    Get the user's country code from their public IP address.

    Returns a two-letter ISO country code (e.g. "US", "CA", "IN") or
    "UNKNOWN" on any failure. Not fail-safe on its own — callers are
    responsible for exception handling (see `record_location`).
    """
    ip_response = httpx.get("https://api.ipify.org", timeout=timeout)
    ip_response.raise_for_status()
    public_ip = ip_response.text.strip()

    response = httpx.get(f"https://api.db-ip.com/v2/free/{public_ip}", timeout=timeout)
    response.raise_for_status()
    data = response.json()

    country_code = data.get("countryCode")
    if country_code is not None and isinstance(country_code, str):
        return country_code.upper()

    return "UNKNOWN"


@dataclass
class MetricInstruments:
    """OpenTelemetry counter instruments."""

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
        service_name: str = PROGRAM_NAME,
        service_version: str | None = None,
        otlp_endpoint: str | None = None,
        export_interval_millis: int = TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS,
        metric_reader: MetricReader | None = None,
    ) -> None:
        """Create a telemetry handler (does not initialize OpenTelemetry yet).

        Parameters
        ----------
        service_name : str
            Service name for metrics (default: `nipoppy.env.PROGRAM_NAME`).
        service_version : str, optional
            Version tag, supplied by the base workflow (default: None).
        otlp_endpoint : str, optional
            Collector endpoint (default: https://telemetry.nipoppy.org).
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
        self.shutdown_called = False

    @property
    def is_enabled(self) -> bool:
        """True if telemetry is initialized and active."""
        return self.metrics is not None

    def initialize(self) -> bool:
        """
        Initialize the meter provider and metric instruments.

        Safe to call multiple times (only initializes once). Returns False if
        initialization is disabled or fails; never raises.
        """
        if self.provider is not None:
            return True

        if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
            return False

        try:
            # OTLP/HTTP exporter uses requests/urllib3 internally; silence both loggers.
            logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)
            logging.getLogger("urllib3").setLevel(logging.CRITICAL)

            if self.service_version is not None and ".dev" not in self.service_version:
                default_environment = "production"
            else:
                default_environment = "development"

            resource = Resource(
                attributes={
                    SERVICE_NAME: self.service_name,
                    SERVICE_VERSION: self.service_version or "unknown",
                    "deployment.environment": os.getenv(
                        "ENVIRONMENT", default_environment
                    ),
                }
            )

            reader = self.metric_reader or self.build_default_reader()

            self.provider = MeterProvider(
                resource=resource,
                metric_readers=[reader],
            )
            meter = self.provider.get_meter(__name__)
            self.metrics = self.create_metric_instruments(meter)

            # Flush and export pending metrics on normal exit and Ctrl+C (SIGINT
            # raises KeyboardInterrupt, which unwinds normally). atexit does not
            # fire on SIGTERM, so that signal gets its own handler below.
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
            if self.metrics is None:
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

    def record_location(self) -> None:
        """Perform a country code lookup and record the country metric."""
        try:
            if self.metrics is None:
                return
            country_code = _get_user_country()
            self.metrics.location_by_country.add(
                1,
                attributes={"country": country_code},
            )
        except Exception as e:
            logger.debug(f"Country lookup failed: {e}")

    def shutdown(self) -> None:
        """Flush and shut down the meter provider. Safe to call multiple times."""
        if self.shutdown_called:
            return
        self.shutdown_called = True
        if self.provider is not None:
            self.provider.shutdown()
