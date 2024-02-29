"""Tests for the parsers."""

from argparse import ArgumentParser

import pytest

from nipoppy.cli.parser import (
    add_arg_dataset_root,
    add_arg_dry_run,
    add_arg_verbosity,
    add_subparser_doughnut,
    add_subparser_init,
    get_global_parser,
)


@pytest.mark.parametrize("dataset_root", ["my_dataset", "dataset_dir"])
def test_add_arg_dataset_root(dataset_root: str):
    parser = ArgumentParser()
    parser = add_arg_dataset_root(parser)
    assert parser.parse_args(["--dataset-root", dataset_root])


def test_add_arg_dry_run():
    parser = ArgumentParser()
    parser = add_arg_dry_run(parser)
    assert parser.parse_args(["--dry-run"])


@pytest.mark.parametrize("verbosity", ["2", "3"])
def test_add_arg_verbosity(verbosity):
    parser = ArgumentParser()
    parser = add_arg_verbosity(parser)
    assert parser.parse_args(["--verbosity", verbosity])


@pytest.mark.parametrize("verbosity", ["4", "x"])
def test_add_arg_verbosity_invalid(verbosity):
    parser = ArgumentParser()
    parser = add_arg_verbosity(parser)
    with pytest.raises(SystemExit) as exception:
        parser.parse_args(["verbosity", verbosity])
    assert exception.value.code != 0, "Parsing of invalid argument should fail."


def test_add_subparser_init():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_init(subparsers)
    assert parser.parse_args(["init", "--dataset-root", "my_dataset"])


@pytest.mark.parametrize(
    "args",
    [
        ["--dataset-root", "my_dataset"],
        ["--dataset-root", "my_dataset", "--empty"],
        ["--dataset-root", "my_dataset", "--regenerate"],
        ["--dataset-root", "my_dataset", "--empty", "--regenerate"],
    ],
)
def test_add_subparser_doughnut(args):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_doughnut(subparsers)
    assert parser.parse_args(["doughnut"] + args)


@pytest.mark.parametrize(
    "args",
    [
        ["-h"],
        ["init", "-h"],
        ["init", "--dataset-root", "my_dataset"],
        ["doughnut", "--dataset-root", "my_dataset", "--regenerate"],
    ],
)
def test_global_parser(args: list[str]):
    parser = get_global_parser()
    try:
        parser.parse_args(args)
    except SystemExit as exception:
        assert (
            exception.code == 0
        ), "Expect exit code of 0 if program exited while parsing."
