"""Tests for the TelemetryHandler class and its module-level helpers."""

from __future__ import annotations

import os
import signal
import threading

import pytest
import pytest_httpx
import pytest_mock
from opentelemetry.sdk.metrics import Counter as SDKCounter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)

from nipoppy.env import (
    TELEMETRY_EXPORT_TIMEOUT_SECONDS,
    TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS,
)
from nipoppy.exceptions import ReturnCode
from nipoppy.workflows.services import telemetry as telemetry_module
from nipoppy.workflows.services.telemetry import (
    TelemetryHandler,
    _get_user_country,
    get_telemetry_handler,
)


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
def _reset_telemetry_singleton():
    """Shut down and clear the module-level singleton between tests."""
    yield
    if telemetry_module._telemetry_handler is not None:
        telemetry_module._telemetry_handler.shutdown()
    telemetry_module._telemetry_handler = None


@pytest.fixture()
def _offline_handler(monkeypatch):
    """Make the singleton's handler use an in-memory reader instead of the network."""
    monkeypatch.setattr(
        TelemetryHandler, "build_default_reader", lambda self: InMemoryMetricReader()
    )


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


class TestInitialize:
    def test_provider_does_not_register_its_own_atexit(self):
        """shutdown_on_exit=False: this class owns the only atexit hook."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        assert handler.provider._atexit_handler is None

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

    @pytest.mark.parametrize(
        "handler_kwargs,failing_method",
        [
            ({}, "build_default_reader"),
            ({"metric_reader": InMemoryMetricReader()}, "create_metric_instruments"),
        ],
    )
    def test_initialize_cleans_up_when_setup_fails(
        self,
        mocker: pytest_mock.MockerFixture,
        handler_kwargs,
        failing_method,
    ):
        """A failure at any point during setup is swallowed, leaving no state."""
        handler = TelemetryHandler(**handler_kwargs)
        mocker.patch.object(handler, failing_method, side_effect=RuntimeError("boom"))

        assert handler.initialize() is False
        assert handler.is_initialized is False
        assert handler.provider is None
        assert handler.metrics is None

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

    @pytest.mark.parametrize(
        "otlp_endpoint",
        [
            "https://collector.example.com",
            "https://collector.example.com/",
            "https://collector.example.com/v1/metrics",
        ],
    )
    def test_metrics_path_is_appended_exactly_once(self, otlp_endpoint):
        """Any spelling of an explicit endpoint resolves to one metrics path."""
        handler = TelemetryHandler(otlp_endpoint=otlp_endpoint)
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://collector.example.com/v1/metrics"

    def test_endpoint_env_var_used_when_not_passed_explicitly(self, monkeypatch):
        """The endpoint environment variable is used when none is passed."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://env.example.com")
        handler = TelemetryHandler()
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://env.example.com/v1/metrics"

    def test_counters_use_delta_temporality(self, monkeypatch):
        """Counters are exported as deltas, without touching the environment."""
        monkeypatch.delenv(
            "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE", raising=False
        )
        reader = TelemetryHandler().build_default_reader()

        assert (
            reader._exporter._preferred_temporality[SDKCounter]
            is AggregationTemporality.DELTA
        )
        assert "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE" not in os.environ

    def test_delta_temporality_survives_a_conflicting_env_var(self, monkeypatch):
        """A user's CUMULATIVE preference cannot break collector accumulation."""
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE", "cumulative"
        )
        reader = TelemetryHandler().build_default_reader()

        assert (
            reader._exporter._preferred_temporality[SDKCounter]
            is AggregationTemporality.DELTA
        )

    @pytest.mark.parametrize(
        "requested,expected",
        [
            (
                TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS + 5000,
                TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS,
            ),
            (
                TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS - 500,
                TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS - 500,
            ),
        ],
    )
    def test_export_interval_is_capped_at_max(self, requested, expected):
        """The export interval is honoured below the maximum and capped above it."""
        handler = TelemetryHandler(export_interval_millis=requested)
        reader = handler.build_default_reader()
        assert reader._export_interval_millis == expected

    def test_export_timeout_is_set(self, monkeypatch):
        """An explicit export timeout keeps a stalled collector from delaying exit."""
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TIMEOUT", raising=False)
        reader = TelemetryHandler().build_default_reader()
        assert reader._exporter._timeout == TELEMETRY_EXPORT_TIMEOUT_SECONDS


class TestCommandCompletion:
    @pytest.mark.parametrize(
        "return_code",
        [ReturnCode.SUCCESS, ReturnCode.UNKNOWN_FAILURE],
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
        assert handler.is_initialized is False

    def test_initialize_returns_false_after_shutdown(self):
        """A shut-down handler cannot be initialized again."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        handler.shutdown()

        assert handler.initialize() is False

    def test_recording_after_shutdown_is_a_no_op(self):
        """Recording after shutdown does not use the closed provider."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        handler.shutdown()

        handler.record_command_completion("init", ReturnCode.SUCCESS)
        handler.record_location_async()
        assert handler._location_thread is None

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


@pytest.mark.usefixtures("_offline_handler")
class TestGetTelemetryHandler:
    """The process-wide singleton accessor."""

    def test_returns_the_same_initialized_handler(self):
        """Repeated calls return one shared, already-initialized handler."""
        handler = get_telemetry_handler()
        assert handler.is_initialized is True
        assert get_telemetry_handler() is handler

    def test_does_not_reinitialize(self):
        """The second call reuses the provider rather than building a new one."""
        provider = get_telemetry_handler().provider
        assert get_telemetry_handler().provider is provider
