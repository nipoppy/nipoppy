"""Tests for nipoppy.env module."""

import importlib
import sys

import pytest

import nipoppy.env


def test_version_unknown(monkeypatch: pytest.MonkeyPatch):
    """Test that PROGRAM_VERSION is 'unknown' when the version file is missing."""
    # raise ImportError
    monkeypatch.setitem(sys.modules, "nipoppy._version", None)

    importlib.reload(nipoppy.env)

    try:
        assert nipoppy.env.PROGRAM_VERSION == "unknown"
    finally:
        # restore the original module
        monkeypatch.undo()
        importlib.reload(nipoppy.env)


def test_version_known():
    """Test that PROGRAM_VERSION is set correctly."""
    assert nipoppy.env.PROGRAM_VERSION != "unknown"
