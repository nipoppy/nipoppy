"""Tests for env module."""

from nipoppy.env import ReturnCode


def test_return_code():
    assert ReturnCode.SUCCESS.value == 0
    assert ReturnCode.ERROR_RUN_SINGLE.value == 1
