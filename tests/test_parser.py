"""Tests for the parsers."""
from argparse import ArgumentParser, HelpFormatter
from pathlib import Path

import pytest
from rich_argparse import RichHelpFormatter

from nipoppy.cli.parser import (
    add_arg_dataset_root,
    add_generic_args,
    get_base_parser,
    get_global_parser,
)


@pytest.fixture(params=["my_dataset", "nipoppy_data"])
def dataset_root(request: pytest.FixtureRequest, tmp_path: Path):
    """Fixture for dataset root."""
    return str(tmp_path / request.param)


@pytest.mark.parametrize("formatter_class", [HelpFormatter, RichHelpFormatter])
def test_base_parser(formatter_class: type[HelpFormatter]):
    """Test parser without args."""
    parser = get_base_parser(formatter_class=formatter_class)
    assert parser.parse_args([]), "Basic parser check not passing."


@pytest.mark.parametrize("args", [["-h"], ["--help"]])
def test_base_parser_help(args):
    """Test parser with help args."""
    parser = get_base_parser()
    with pytest.raises(SystemExit) as exception:
        parser.parse_args(args)
    assert exception.value.code == 0, "Help should exit with code 0."


@pytest.mark.parametrize("flag", ["--dataset_root", "--dataset-root"])
def test_add_arg_dataset_root(flag: str, dataset_root: Path):
    """Check dataset_root argument."""
    parser = ArgumentParser()
    parser = add_arg_dataset_root(parser)
    args = [flag, dataset_root]
    assert parser.parse_args(args), "Dataset root argument not parse correctly."


@pytest.mark.parametrize("args", [["--verbosity", "2"], ["--verbosity", "3"]])
def test_add_generic_args(args):
    """Check generic arguments."""
    parser = ArgumentParser()
    parser = add_generic_args(parser)
    assert parser.parse_args(args), "Generic argument(s) not recognized."


@pytest.mark.parametrize("args", [["--verbosity", "4"], ["--verbosity", "x"]])
def test_add_generic_args_errors(args):
    """Test invalid generic argument values."""
    parser = ArgumentParser()
    parser = add_generic_args(parser)
    with pytest.raises(SystemExit) as exception:
        parser.parse_args(args)
    assert exception.value.code != 0, "Parsing of invalid argument should fail."


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
