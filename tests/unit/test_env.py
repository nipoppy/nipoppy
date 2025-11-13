"""Tests for env module."""

from nipoppy.env import ReturnCode
from nipoppy.logger import LogColor


def test_return_code():
    assert ReturnCode.SUCCESS == 0
    assert ReturnCode.UNKNOWN_FAILURE == 1
    assert ReturnCode.PARTIAL_SUCCESS == 64


def test_color():
    assert LogColor.SUCCESS == "green"
    assert LogColor.PARTIAL_SUCCESS == "yellow"
    assert LogColor.FAILURE == "red"
