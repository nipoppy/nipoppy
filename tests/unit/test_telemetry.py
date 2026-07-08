"""Tests for the TelemetryHandler class.

Telemetry must be non-confounding: if it is disabled, uninitialized, or
fails internally, it must never raise and never disrupt the caller.
"""

import pytest
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from nipoppy.exceptions import ReturnCode
from nipoppy.telemetry import TelemetryHandler


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


class TestFailSafe:
    """Telemetry must never raise, even when broken or uninitialized."""

    def test_record_command_completion_does_not_raise_when_uninitialized(self):
        """Recording a command completion before init is a silent no-op."""
        handler = TelemetryHandler()
        # Never initialized — must be a silent no-op, not an error.
        handler.record_command_completion("init", ReturnCode.SUCCESS)

    def test_record_location_does_not_raise_when_uninitialized(self):
        """Recording a location before init is a silent no-op."""
        handler = TelemetryHandler()
        handler.record_location()

    def test_is_enabled_false_before_initialize(self):
        """A handler is not enabled until initialize() is called."""
        handler = TelemetryHandler()
        assert handler.is_enabled is False


class TestInitialize:
    def test_initialize_returns_true_with_in_memory_reader(self):
        """initialize() succeeds and enables the handler with a valid reader."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        assert handler.initialize() is True
        assert handler.is_enabled is True

    def test_initialize_returns_false_when_sdk_disabled(self, monkeypatch):
        """OTEL_SDK_DISABLED=true disables initialization."""
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        assert handler.initialize() is False
        assert handler.is_enabled is False

    def test_initialize_is_idempotent(self):
        """Calling initialize() more than once is safe and stays enabled."""
        handler = TelemetryHandler(metric_reader=InMemoryMetricReader())
        assert handler.initialize() is True
        assert handler.initialize() is True


class TestCommandCompletion:
    @pytest.mark.parametrize(
        "return_code,expected_status",
        [
            (ReturnCode.SUCCESS, "success"),
            (ReturnCode.PARTIAL_SUCCESS, "partial"),
            (ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN, "partial"),
            (ReturnCode.UNKNOWN_FAILURE, "failure"),
        ],
    )
    def test_status_mapping(self, return_code, expected_status):
        """Return codes map to the expected success/partial/failure status."""
        reader = InMemoryMetricReader()
        handler = TelemetryHandler(metric_reader=reader)
        handler.initialize()

        handler.record_command_completion("run", return_code)

        points = _data_points(reader, "commands.completed")
        assert len(points) == 1
        assert points[0].value == 1
        assert points[0].attributes["command"] == "run"
        assert points[0].attributes["status"] == expected_status


class TestLocation:
    def test_record_location_uses_country_lookup(self, monkeypatch):
        """record_location() emits a country metric from the GeoIP lookup."""
        reader = InMemoryMetricReader()
        handler = TelemetryHandler(metric_reader=reader)
        handler.initialize()

        monkeypatch.setattr("nipoppy.telemetry.handler.get_user_country", lambda: "CA")
        handler.record_location()

        points = _data_points(reader, "location.by_country")
        assert len(points) == 1
        assert points[0].value == 1
        assert points[0].attributes["country"] == "CA"
