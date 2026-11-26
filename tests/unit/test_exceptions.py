"""Tests for custom exceptions."""

import json
from pathlib import Path

from nipoppy.exceptions import JSONError, NipoppyError


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

    class SubclassError(NipoppyError):
        default_hint = "default hint"

    err = SubclassError("test message")
    assert err.hint is None
    assert err.troubleshooting_hint == err.default_hint


def test_json_error_message_includes_fpath():
    """JSONError should include the file path in its error message."""
    fpath = "invalid.json"
    err = JSONError(json.JSONDecodeError("Invalid JSON", "{}", 10), fpath=Path(fpath))
    assert str(err) == f"Invalid JSON: {fpath}: line 1 column 11 (char 10)"
