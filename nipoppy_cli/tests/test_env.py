"""Tests for env module."""

from nipoppy.env import LogColor, ReturnCode


def test_return_code():
    assert ReturnCode.SUCCESS == 0
    assert ReturnCode.ERROR_RUN_SINGLE == 1


def test_color():
    assert LogColor.SUCCESS == "green"
    assert LogColor.PARTIAL_SUCCESS == "yellow"
    assert LogColor.FAILURE == "red"
