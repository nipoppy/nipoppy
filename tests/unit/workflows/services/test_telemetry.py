"""Tests for the nipoppy.workflows.services.telemetry module."""

from __future__ import annotations

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
    TELEMETRY_MAX_EXPORT_INTERVAL_MILLIS,
)
from nipoppy.exceptions import ReturnCode
from nipoppy.workflows.services import telemetry as telemetry_module
from nipoppy.workflows.services.telemetry import (
    _get_user_country,
    _TelemetryHandler,
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
        _TelemetryHandler, "build_default_reader", lambda self: InMemoryMetricReader()
    )


@pytest.fixture()
def _restore_sigterm():
    """Prevent SIGTERM handlers registered by initialize() from leaking across tests."""
    original = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, original)


class TestGetUserCountry:
    """Testing related to the db-ip country lookup."""

    def test_returns_uppercased_country_code(self, httpx_mock: pytest_httpx.HTTPXMock):
        """The country code from db-ip is returned in upper case."""
        httpx_mock.add_response(
            url="https://api.db-ip.com/v2/free/self",
            json={"countryCode": "ca"},
        )
        assert len(_get_user_country()) == 2


class TestFailSafe:
    """_TelemetryHandler must never raise, even when broken or uninitialized."""

    def test_record_command_completion_does_not_raise_when_uninitialized(self):
        """Recording a command before setup does nothing and does not raise."""
        handler = _TelemetryHandler()
        handler.record_command_completion("init", ReturnCode.SUCCESS)

    def test_record_location_does_not_raise_when_uninitialized(self):
        """Recording the location before setup does nothing and starts no lookup."""
        handler = _TelemetryHandler()
        handler.record_location_async()
        assert handler._location_thread is None


class TestInitialize:
    """Setting up telemetry with initialize()."""

    def test_provider_does_not_register_its_own_atexit(self):
        """Telemetry is flushed once at exit, by _TelemetryHandler only."""
        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        assert handler.provider._atexit_handler is None

    def test_initialize_is_idempotent(self):
        """Running setup twice is safe."""
        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
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
        """If setup fails, no error is raised and telemetry stays off."""
        handler = _TelemetryHandler(**handler_kwargs)
        mocker.patch.object(handler, failing_method, side_effect=RuntimeError("boom"))

        assert handler.initialize() is False
        assert handler.is_initialized is False
        assert handler.provider is None
        assert handler.metrics is None


class TestBuildDefaultReader:
    """Where metrics are sent, and how often."""

    @pytest.mark.parametrize(
        "otlp_endpoint",
        [
            "https://collector.example.com",
            "https://collector.example.com/",
            "https://collector.example.com/v1/metrics",
        ],
    )
    def test_metrics_path_is_appended_exactly_once(self, otlp_endpoint):
        """A custom collector URL works with or without the /v1/metrics path."""
        handler = _TelemetryHandler(otlp_endpoint=otlp_endpoint)
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://collector.example.com/v1/metrics"
        reader.shutdown()

    def test_endpoint_env_var_is_ignored(self, monkeypatch):
        """OTEL_EXPORTER_OTLP_ENDPOINT cannot change the collector URL."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://env.example.com")
        handler = _TelemetryHandler()
        reader = handler.build_default_reader()
        assert reader._exporter._endpoint == "https://telemetry.nipoppy.org/v1/metrics"
        reader.shutdown()

    def test_delta_temporality_survives_a_conflicting_env_var(self, monkeypatch):
        """A user's temporality setting cannot switch counters away from delta."""
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE", "cumulative"
        )
        reader = _TelemetryHandler().build_default_reader()

        assert (
            reader._exporter._preferred_temporality[SDKCounter]
            is AggregationTemporality.DELTA
        )
        reader.shutdown()

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
        """The export interval cannot go above the maximum."""
        handler = _TelemetryHandler(export_interval_millis=requested)
        reader = handler.build_default_reader()
        assert reader._export_interval_millis == expected
        reader.shutdown()


class TestCommandCompletion:
    """Counting finished commands."""

    @pytest.mark.parametrize(
        "return_code",
        [ReturnCode.SUCCESS, ReturnCode.UNKNOWN_FAILURE],
    )
    def test_status_mapping(self, return_code):
        """A finished command is counted with its name, status and return code."""
        reader = InMemoryMetricReader()
        handler = _TelemetryHandler(metric_reader=reader)
        handler.initialize()

        handler.record_command_completion("run", return_code)

        points = _data_points(reader, "commands.completed")
        assert len(points) == 1
        assert points[0].value == 1
        assert points[0].attributes["command"] == "run"
        assert points[0].attributes["status"] == return_code.name
        assert points[0].attributes["return_code"] == str(return_code.value)

    def test_does_not_raise_when_recording_fails(self, monkeypatch):
        """A failure while counting a command does not reach the user."""
        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        monkeypatch.setattr(
            handler.metrics.commands_completed,
            "add",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        handler.record_command_completion("run", ReturnCode.SUCCESS)


class TestLocation:
    """Recording the user's country in the background."""

    def test_record_location_uses_country_lookup(self, monkeypatch):
        """The country from the lookup is recorded."""
        reader = InMemoryMetricReader()
        handler = _TelemetryHandler(metric_reader=reader)
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
        assert len(points[0].attributes["country"]) == 2

    def test_does_not_raise_when_lookup_fails(self, monkeypatch):
        """If the lookup fails, nothing is recorded and no error is raised."""
        reader = InMemoryMetricReader()
        handler = _TelemetryHandler(metric_reader=reader)
        handler.initialize()

        monkeypatch.setattr(
            "nipoppy.workflows.services.telemetry._get_user_country",
            lambda timeout=None: (_ for _ in ()).throw(RuntimeError("network down")),
        )
        handler.record_location_async()
        handler._location_thread.join(timeout=5)

        assert _data_points(reader, "location.by_country") == []

    def test_record_location_async_returns_before_lookup_completes(self, monkeypatch):
        """The call returns while the lookup is still running."""
        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()

        # Keeps the fake lookup running until the test releases it.
        release = threading.Event()

        def _blocking_lookup(timeout=None):
            release.wait(timeout=5)
            return "CA"

        monkeypatch.setattr(
            "nipoppy.workflows.services.telemetry._get_user_country", _blocking_lookup
        )
        handler.record_location_async()

        # Make sure the worker is still blocked on the event.
        assert handler._location_thread.is_alive()

        release.set()
        handler._location_thread.join(timeout=5)
        assert not handler._location_thread.is_alive()


class TestShutdown:
    """Flushing and closing telemetry at exit."""

    def test_shutdown_is_safe_before_initialize(self):
        """Shutdown works even if setup never ran."""
        handler = _TelemetryHandler()
        handler.shutdown()
        assert handler.shutdown_called is True

    def test_shutdown_flushes_provider(self, mocker):
        """Shutdown sends pending metrics and turns telemetry off."""
        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        spy = mocker.spy(handler.provider, "shutdown")

        handler.shutdown()

        spy.assert_called_once()
        assert handler.shutdown_called is True
        assert handler.is_initialized is False

    def test_initialize_returns_false_after_shutdown(self):
        """Telemetry cannot be set up again after shutdown."""
        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        handler.shutdown()

        assert handler.initialize() is False

    def test_recording_after_shutdown_is_a_no_op(self):
        """Nothing is recorded after shutdown."""
        reader = InMemoryMetricReader()
        handler = _TelemetryHandler(metric_reader=reader)
        handler.initialize()
        handler.shutdown()

        handler.record_command_completion("init", ReturnCode.SUCCESS)
        handler.record_location_async()

        assert _data_points(reader, "commands.completed") == []
        assert _data_points(reader, "location.by_country") == []

    def test_shutdown_is_idempotent(self, mocker):
        """Running shutdown twice closes the provider only once."""
        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        spy = mocker.spy(handler.provider, "shutdown")

        handler.shutdown()
        handler.shutdown()

        spy.assert_called_once()


@pytest.mark.usefixtures("_restore_sigterm")
class TestSigtermHandler:
    """initialize() installs a SIGTERM handler that flushes telemetry on exit."""

    def test_calls_shutdown_and_delegates_to_previous_handler(
        self, mocker: pytest_mock.MockerFixture
    ):
        """SIGTERM flushes telemetry, then still runs the previous handler."""
        original_handler = mocker.Mock()
        signal.signal(signal.SIGTERM, original_handler)

        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        spy_shutdown = mocker.spy(handler, "shutdown")

        installed_handler = signal.getsignal(signal.SIGTERM)
        installed_handler(signal.SIGTERM, None)

        spy_shutdown.assert_called_once()
        original_handler.assert_called_once_with(signal.SIGTERM, None)

    def test_exits_when_no_previous_handler(self, mocker: pytest_mock.MockerFixture):
        """SIGTERM flushes telemetry, then exits if there is no previous handler."""
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        handler = _TelemetryHandler(metric_reader=InMemoryMetricReader())
        handler.initialize()
        spy_shutdown = mocker.spy(handler, "shutdown")
        mock_exit = mocker.patch("nipoppy.workflows.services.telemetry.sys.exit")

        installed_handler = signal.getsignal(signal.SIGTERM)
        installed_handler(signal.SIGTERM, None)

        spy_shutdown.assert_called_once()
        mock_exit.assert_called_once_with(0)


@pytest.mark.usefixtures("_offline_handler")
class TestGetTelemetryHandler:
    """The shared telemetry handler for the whole process."""

    def test_returns_the_same_initialized_handler(self):
        """Every call returns the same handler, ready to use."""
        handler = get_telemetry_handler()
        assert handler.is_initialized is True
        assert get_telemetry_handler() is handler

    def test_does_not_reinitialize(self):
        """Later calls do not set up telemetry again."""
        provider = get_telemetry_handler().provider
        assert get_telemetry_handler().provider is provider
