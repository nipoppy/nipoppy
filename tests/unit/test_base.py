"""Tests for the base module."""

import pytest

from nipoppy.base import Base


class BaseA(Base):
    def __init__(self, pos_arg, kw_arg=None, *args, **kwargs):
        self.pos_arg = pos_arg
        self.kw_arg = kw_arg


class BaseB(Base):
    def __init__(self, arg1, arg2=2, arg3="3"):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3


class BadBase(Base):
    def __init__(self, arg):
        pass


@pytest.mark.parametrize(
    "base,components,names,sep,expected",
    [
        (BaseA(1), ["x", "y"], None, ", ", "BaseA(x, y)"),
        (BaseA(1), None, ["pos_arg"], "-", "BaseA(pos_arg=1)"),
        (BaseB(1), None, None, ", ", "BaseB()"),
    ],
)
def test_str_helper(base: Base, components, names, sep, expected):
    assert base._str_helper(components, names, sep) == expected


@pytest.mark.parametrize(
    "base,expected",
    [
        (BaseA(1), "BaseA(pos_arg=1, kw_arg=None)"),
        (BaseA("a"), "BaseA(pos_arg=a, kw_arg=None)"),
        (BaseB(1), "BaseB(arg1=1, arg2=2, arg3=3)"),
        (BaseB("B"), "BaseB(arg1=B, arg2=2, arg3=3)"),
    ],
)
def test_str_and_repr(base: Base, expected):
    assert str(base) == expected
    assert repr(base) == expected


def test_str_error():
    with pytest.raises(RuntimeError, match="Failed to build string representation"):
        str(BadBase(1))
