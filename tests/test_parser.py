"""Tests for the parsers."""
from argparse import HelpFormatter

import pytest
from rich_argparse import RichHelpFormatter

from nipoppy.cli.parser import get_base_parser, get_global_parser


@pytest.mark.parametrize(
    "formatter_class",
    [
        HelpFormatter,
        RichHelpFormatter,
    ],
)
def test_base_parser(formatter_class: type[HelpFormatter]):
    """Test parser without args."""
    parser = get_base_parser(formatter_class=formatter_class)
    parser.parse_args([])


@pytest.mark.parametrize(
    "args",
    [
        ["-h"],
        ["--help"],
    ],
)
def test_base_parser_help(args):
    """Test parser with help args."""
    parser = get_base_parser()
    with pytest.raises(SystemExit) as exception:
        parser.parse_args(args)
    assert exception.value.code == 0, "Help should exit with code 0."


@pytest.mark.parametrize(
    "args",
    [
        [],
    ],
)
def test_global_parser(args: list[str]):
    """Test global parser."""
    parser = get_global_parser()
    parser.parse_args(args)
