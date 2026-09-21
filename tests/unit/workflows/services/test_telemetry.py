"""Tests for the TelemetryHandler class and its module-level helpers."""

from __future__ import annotations

import os
import signal
import threading

import pytest
import pytest_httpx
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from nipoppy.env import TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS
from nipoppy.exceptions import ReturnCode
from nipoppy.workflows.services.telemetry import TelemetryHandler, _get_user_country


def _data_points(reader: InMemoryMetricReader, metric_name: str):
    """Collect data points for a given metric name from an in-memory reader."""
    points = []
    data = reader.get_metrics_data()
    if data is None:
        return points
    for resource_metric in data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == metric_name:
                    points.extend(metric.data.data_points)
    return points


@pytest.fixture(autouse=True)
def _restore_sigterm():
    """Prevent SIGTERM handlers registered by initialize() from leaking across tests."""
    original = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, original)


class TestGetUserCountry:
    """Direct tests of the module-level GeoIP lookup helper."""

    def test_returns_uppercased_country_code(self, httpx_mock: pytest_httpx.HTTPXMock):
        """A lowercase country code from the API is upper-cased."""
        httpx_mock.add_response(
            url="https://api.db-ip.com/v2/free/self",
            json={"countryCode": "ca"},
        )
        assert _get_user_country() == "CA"

    def test_raises_when_lookup_fails(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Not fail-safe on its own: callers (record_location) handle exceptions."""
        httpx_mock.add_exception(
            Exception("geoip down"), url="https://api.db-ip.com/v2/free/self"
        )
        with pytest.raises(Exception, match="geoip down"):
            _get_user_country()

    def test_raises_when_country_code_missing(self, httpx_mock: pytest_httpx.HTTPXMock):
        """No countryCode in the payload means there is nothing to upper-case."""
        httpx_mock.add_response(
            url="https://api.db-ip.com/v2/free/self",
            json={"ipAddress": "1.2.3.4"},
        )
        with pytest.raises(AttributeError):
            _get_user_country()


class TestFailSafe:
    """Telemetry must never raise, even when broken or uninitialized."""

    def test_record_command_completion_does_not_raise_when_uninitialized(self):
        """Recording a command completion before init is a silent no-op."""
        handler = TelemetryHandler()
        # Never initialized — must be a silent no-op, not an error.
        handler.record_command_completion("init", ReturnCode.SUCCESS)

    def test_record_location_does_not_raise_when_uninitialized(self):
        """Recording a location before init is a silent no-op, with no thread."""
        handler = TelemetryHandler()
        handler.record_location_async()
        assert handler._location_thread is None

    def test_is_initialized_false_before_initialize(self):
        """A handler is not initialized until initialize() is called."""
        handler = TelemetryHandler()
        assert handler.is_initialized is False


class TestInitialize:
    def test_initialize_returns_true_with_in_memory_reader(self):
        """initialize() succeeds and initializes the handler with a valid reader."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        assert handler.initialize() is True
        assert handler.is_initialized is True

    def test_initialize_returns_false_when_sdk_disabled(self, monkeypatch):
        """OTEL_SDK_DISABLED=true disables initialization."""
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        assert handler.initialize() is False
        assert handler.is_initialized is False

    def test_initialize_is_idempotent(self):
        """Calling initialize() more than once is safe and stays initialized."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        assert handler.initialize() is True
        assert handler.initialize() is True

    def test_initialize_returns_false_on_unexpected_error(self, monkeypatch):
        """Any failure while building the provider/reader is swallowed."""
        handler = TelemetryHandler()
        monkeypatch.setattr(
            handler,
            "build_default_reader",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        assert handler.initialize() is False
        assert handler.is_initialized is False
        assert handler.provider is None

    @pytest.mark.parametrize(
        "service_version,expected_environment",
        [
            (None, "development"),
            ("1.2.3", "production"),
            ("1.2.3.dev0", "development"),
        ],
    )
    def test_default_deployment_environment_from_version(
        self, service_version, expected_environment
    ):
        """Version string decides development vs production environment."""
        handler = TelemetryHandler(
            service_version=service_version, metric_reader=InMemoryMetricReader()
        )
        handler.initialize()
        resource_attrs = handler.provider._sdk_config.resource.attributes
        assert resource_attrs["deployment.environment"] == expected_environment

    def test_environment_variable_overrides_default(self, monkeypatch):
        """ENVIRONMENT overrides the version-derived deployment environment."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        handler = TelemetryHandler(
            service_version="1.2.3", metric_reader=InMemoryMetricReader()
        )
        handler.initialize()
        resource_attrs = handler.provider._sdk_config.resource.attributes
        assert resource_attrs["deployment.environment"] == "staging"

    def test_service_version_defaults_to_unknown(self):
        """An absent service version is reported as unknown."""
        handler = TelemetryHandler(
            service_version=None, metric_reader=InMemoryMetricReader()
        )
        handler.initialize()
        resource_attrs = handler.provider._sdk_config.resource.attributes
        assert resource_attrs["service.version"] == "unknown"


class TestBuildDefaultReader:
    """The default OTLP/HTTP reader is built with the right endpoint and cadence."""

    def test_default_endpoint(self, monkeypatch):
        """With nothing configured, the default collector endpoint is used."""
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        handler = TelemetryHandler()
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://telemetry.nipoppy.org/v1/metrics"

    def test_explicit_endpoint_gets_metrics_path_appended(self):
        """An explicit endpoint gets the metrics path appended."""
        handler = TelemetryHandler(otlp_endpoint="https://collector.example.com")
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://collector.example.com/v1/metrics"

    def test_trailing_slash_is_stripped_before_appending(self):
        """A trailing slash is stripped before the metrics path is appended."""
        handler = TelemetryHandler(otlp_endpoint="https://collector.example.com/")
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://collector.example.com/v1/metrics"

    def test_endpoint_already_ending_in_metrics_path_is_unchanged(self):
        """An endpoint already ending in the metrics path is left unchanged."""
        handler = TelemetryHandler(
            otlp_endpoint="https://collector.example.com/v1/metrics"
        )
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://collector.example.com/v1/metrics"

    def test_endpoint_env_var_used_when_not_passed_explicitly(self, monkeypatch):
        """The endpoint environment variable is used when none is passed."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://env.example.com")
        handler = TelemetryHandler()
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://env.example.com/v1/metrics"

    def test_sets_delta_temporality_preference(self, monkeypatch):
        """The reader requests delta temporality from the exporter."""
        monkeypatch.delenv(
            "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE", raising=False
        )
        handler = TelemetryHandler()
        handler.build_default_reader()
        assert (
            os.environ["OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"] == "delta"
        )

    def test_export_interval_is_capped_at_max(self):
        """An oversized export interval is capped at the maximum."""
        handler = TelemetryHandler(
            export_interval_millis=TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS + 5000
        )
        reader = handler.build_default_reader()
        assert reader._export_interval_millis == TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS

    def test_export_interval_below_max_is_kept(self):
        """An export interval below the maximum is left unchanged."""
        handler = TelemetryHandler(
            export_interval_millis=TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS - 500
        )
        reader = handler.build_default_reader()
        assert (
            reader._export_interval_millis == TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS - 500
        )


class TestCommandCompletion:
    @pytest.mark.parametrize(
        "return_code",
        [
            ReturnCode.SUCCESS,
            ReturnCode.PARTIAL_SUCCESS,
            ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN,
            ReturnCode.UNKNOWN_FAILURE,
        ],
    )
    def test_status_mapping(self, return_code):
        """Return codes map to their enum name/value as status/return_code."""
        reader = InMemoryMetricReader()
        handler = TelemetryHandler(metric_reader=reader)
        handler.initialize()

        handler.record_command_completion("run", return_code)

        points = _data_points(reader, "commands.completed")
        assert len(points) == 1
        assert points[0].value == 1
        assert points[0].attributes["command"] == "run"
        assert points[0].attributes["status"] == return_code.name
        assert points[0].attributes["return_code"] == str(return_code.value)

    def test_does_not_raise_when_recording_fails(self, monkeypatch):
        """A broken counter must not propagate an exception to the caller."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        monkeypatch.setattr(
            handler.metrics.commands_completed,
            "add",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        handler.record_command_completion("run", ReturnCode.SUCCESS)


class TestLocation:
    def test_record_location_uses_country_lookup(self, monkeypatch):
        """record_location() emits a country metric from the GeoIP lookup."""
        reader = InMemoryMetricReader()
        handler = TelemetryHandler(metric_reader=reader)
        handler.initialize()

        monkeypatch.setattr(
            "nipoppy.workflows.services.telemetry._get_user_country",
            lambda timeout=None: "CA",
        )
        handler.record_location_async()
        handler._location_thread.join(timeout=5)

        points = _data_points(reader, "location.by_country")
        assert len(points) == 1
        assert points[0].value == 1
        assert points[0].attributes["country"] == "CA"

    def test_does_not_raise_when_lookup_fails(self, monkeypatch):
        """A failing country lookup records nothing and does not raise."""
        reader = InMemoryMetricReader()
        handler = TelemetryHandler(metric_reader=reader)
        handler.initialize()

        monkeypatch.setattr(
            "nipoppy.workflows.services.telemetry._get_user_country",
            lambda timeout=None: (_ for _ in ()).throw(RuntimeError("network down")),
        )
        handler.record_location_async()
        handler._location_thread.join(timeout=5)

        assert _data_points(reader, "location.by_country") == []

    def test_record_location_async_returns_before_lookup_completes(self, monkeypatch):
        """The call returns while the lookup is still in flight."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()

        release = threading.Event()

        def _blocking_lookup(timeout=None):
            release.wait(timeout=5)
            return "CA"

        monkeypatch.setattr(
            "nipoppy.workflows.services.telemetry._get_user_country", _blocking_lookup
        )
        handler.record_location_async()

        # Control is back here while the worker is still blocked on the event.
        assert handler._location_thread.is_alive()

        release.set()
        handler._location_thread.join(timeout=5)
        assert not handler._location_thread.is_alive()

    def test_shutdown_joins_location_thread(self, monkeypatch):
        """shutdown() waits for the lookup instead of abandoning it."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()

        monkeypatch.setattr(
            "nipoppy.workflows.services.telemetry._get_user_country",
            lambda timeout=None: "CA",
        )
        handler.record_location_async()
        handler.shutdown()

        assert handler._location_thread.is_alive() is False


class TestShutdown:
    def test_shutdown_is_safe_before_initialize(self):
        """shutdown() before initialize() still marks the handler shut down."""
        handler = TelemetryHandler()
        handler.shutdown()
        assert handler.shutdown_called is True

    def test_shutdown_flushes_provider(self, mocker):
        """shutdown() shuts down the underlying meter provider."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        spy = mocker.spy(handler.provider, "shutdown")

        handler.shutdown()

        spy.assert_called_once()
        assert handler.shutdown_called is True

    def test_shutdown_is_idempotent(self, mocker):
        """Calling shutdown() twice shuts the provider down only once."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        spy = mocker.spy(handler.provider, "shutdown")

        handler.shutdown()
        handler.shutdown()

        spy.assert_called_once()


class TestSigtermHandler:
    """initialize() installs a SIGTERM handler that flushes telemetry on exit."""

    def test_calls_shutdown_and_delegates_to_previous_handler(self, mocker):
        """The handler flushes telemetry, then calls the previous SIGTERM handler."""
        original_handler = mocker.Mock()
        signal.signal(signal.SIGTERM, original_handler)

        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()

        installed_handler = signal.getsignal(signal.SIGTERM)
        installed_handler(signal.SIGTERM, None)

        assert handler.shutdown_called is True
        original_handler.assert_called_once_with(signal.SIGTERM, None)

    def test_exits_when_no_previous_handler(self, monkeypatch, mocker):
        """With no previous handler, the process exits cleanly after flushing."""
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()

        mock_exit = mocker.Mock()
        monkeypatch.setattr("nipoppy.workflows.services.telemetry.sys.exit", mock_exit)

        installed_handler = signal.getsignal(signal.SIGTERM)
        installed_handler(signal.SIGTERM, None)

        assert handler.shutdown_called is True
        mock_exit.assert_called_once_with(0)
