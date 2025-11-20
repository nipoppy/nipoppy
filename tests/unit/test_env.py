"""Tests for env module."""

from nipoppy.env import ReturnCode


def test_return_code():
    assert ReturnCode.SUCCESS == 0
    assert ReturnCode.UNKNOWN_FAILURE == 1
    assert ReturnCode.PARTIAL_SUCCESS == 64
