"""Tests for custom exceptions."""

from nipoppy.exceptions import ConfigError, NipoppyError


def test_troubleshooting_hint_none_without_default():
    """NipoppyError without a default or custom hint should have no hint."""
    err = NipoppyError("test message")
    assert err.default_hint is None
    assert err.hint is None
    assert err.troubleshooting_hint is None


def test_troubleshooting_hint_custom():
    """A custom hint should take precedence."""
    err = NipoppyError("test message", hint="custom hint")
    assert err.troubleshooting_hint == "custom hint"


def test_troubleshooting_hint_subclass_default():
    """Subclasses with a default_hint should use it when no hint is given."""
    err = ConfigError("test message")
    assert err.troubleshooting_hint == ConfigError.default_hint
    assert err.troubleshooting_hint is not None
