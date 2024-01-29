"""Tests for the parsers."""
from argparse import ArgumentParser

import pytest

from nipoppy.cli.parser import (
    add_arg_dataset_root,
    add_arg_verbosity,
    add_subparser_init,
    get_global_parser,
)


@pytest.mark.parametrize("flag", ["--dataset_root", "--dataset-root"])
@pytest.mark.parametrize("dataset_root", ["my_dataset", "dataset_dir"])
def test_add_arg_dataset_root(flag: str, dataset_root: str):
    """Check dataset_root argument."""
    parser = ArgumentParser()
    parser = add_arg_dataset_root(parser)
    assert parser.parse_args([flag, dataset_root])


@pytest.mark.parametrize("verbosity", ["2", "3"])
def test_add_arg_verbosity(verbosity):
    """Check generic arguments."""
    parser = ArgumentParser()
    parser = add_arg_verbosity(parser)
    assert parser.parse_args(["--verbosity", verbosity])


@pytest.mark.parametrize("verbosity", ["4", "x"])
def test_add_arg_verbosity_invalid(verbosity):
    """Test invalid generic argument values."""
    parser = ArgumentParser()
    parser = add_arg_verbosity(parser)
    with pytest.raises(SystemExit) as exception:
        parser.parse_args(["verbosity", verbosity])
    assert exception.value.code != 0, "Parsing of invalid argument should fail."


def test_add_subparser_init():
    """Test init subparser."""
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_init(subparsers)
    assert parser.parse_args(["init", "--dataset-root", "my_dataset"])


@pytest.mark.parametrize(
    "args",
    [
        ["-h"],
        ["init", "-h"],
        ["init", "--dataset-root", "my_dataset"],
    ],
)
def test_global_parser(args: list[str]):
    """Test global parser."""
    parser = get_global_parser()
    try:
        parser.parse_args(args)
    except SystemExit as exception:
        assert (
            exception.code == 0
        ), "Expect exit code of 0 if program exited while parsing."
