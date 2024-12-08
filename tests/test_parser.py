"""Tests for the parsers."""

from argparse import ArgumentParser

import pytest

from nipoppy.cli.parser import (
    add_arg_dataset_root,
    add_arg_dry_run,
    add_arg_verbosity,
    add_arg_version,
    add_args_participant_and_session,
    add_args_pipeline,
    add_subparser_bidsify,
    add_subparser_doughnut,
    add_subparser_extract,
    add_subparser_init,
    add_subparser_reorg,
    add_subparser_run,
    add_subparser_status,
    add_subparser_track,
    get_global_parser,
)


@pytest.mark.parametrize("dataset_root", ["my_dataset", "dataset_dir"])
def test_add_arg_dataset_root(dataset_root: str):
    parser = ArgumentParser()
    parser = add_arg_dataset_root(parser)
    assert parser.parse_args([dataset_root])


def test_add_arg_version():
    parser = ArgumentParser()
    parser = add_arg_version(parser)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        parser.parse_args(["--version"])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0


@pytest.mark.parametrize(
    "args",
    [
        ["--pipeline", "my_pipeline"],
        ["--pipeline", "my_other_pipeline", "--pipeline-version", "1.0.0"],
        ["--pipeline", "my_other_pipeline", "--pipeline-step", "step1"],
    ],
)
def test_add_args_pipeline(args):
    parser = ArgumentParser()
    parser = add_args_pipeline(parser)
    assert parser.parse_args(args)


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--participant-id", "1000"],
        ["--session-id", "1"],
        ["--participant-id", "sub-123", "--session-id", "ses-1"],
    ],
)
def test_add_args_participant_and_session(args):
    parser = ArgumentParser()
    parser = add_args_participant_and_session(parser)
    assert parser.parse_args(args)


def test_add_arg_dry_run():
    parser = ArgumentParser()
    parser = add_arg_dry_run(parser)
    assert parser.parse_args(["--dry-run"])


@pytest.mark.parametrize("verbosity", ["2", "3"])
def test_add_arg_verbosity(verbosity):
    parser = ArgumentParser()
    parser = add_arg_verbosity(parser)
    assert parser.parse_args(["--verbosity", verbosity])


def test_add_arg_verbosity_invalid(capsys: pytest.CaptureFixture):
    parser = ArgumentParser()
    parser = add_arg_verbosity(parser)
    with pytest.raises(SystemExit) as exception:
        parser.parse_args(["--verbosity", "4"])

    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
    assert exception.value.code != 0, "Parsing of invalid argument should fail."


def test_add_subparser_init():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_init(subparsers)
    assert parser.parse_args(["init", "my_dataset"])


def test_add_subparser_status():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_status(subparsers)
    assert parser.parse_args(["status", "my_dataset"])


@pytest.mark.parametrize(
    "args",
    [
        ["my_dataset"],
        ["my_dataset", "--empty"],
        ["my_dataset", "--regenerate"],
        ["my_dataset", "--empty", "--regenerate"],
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
        ["my_dataset"],
        ["my_dataset", "--copy-files"],
        ["my_dataset", "--check-dicoms"],
    ],
)
def test_add_subparser_reorg(args):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_reorg(subparsers)
    assert parser.parse_args(["reorg"] + args)


@pytest.mark.parametrize(
    "args",
    [
        ["my_dataset", "--pipeline", "pipeline1"],
        ["my_dataset", "--pipeline", "pipeline1", "--simulate"],
        [
            "my_dataset",
            "--pipeline",
            "pipeline1",
            "--pipeline-step",
            "step1",
        ],
    ],
)
def test_add_subparser_bidsify(args):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_bidsify(subparsers)
    assert parser.parse_args(["bidsify"] + args)


@pytest.mark.parametrize(
    "args",
    [
        ["my_dataset", "--pipeline", "pipeline1"],
        ["my_dataset", "--pipeline", "pipeline1", "--simulate"],
        [
            "my_dataset",
            "--pipeline",
            "pipeline1",
            "--pipeline-version",
            "1.2.3",
        ],
        [
            "my_dataset",
            "--pipeline",
            "pipeline1",
            "--pipeline-version",
            "1.2.3",
            "--pipeline-step",
            "step1",
        ],
        [
            "my_dataset",
            "--pipeline",
            "pipeline2",
            "--participant-id",
            "1000",
        ],
        [
            "my_dataset",
            "--pipeline",
            "pipeline2",
            "--participant-id",
            "1000",
            "--session-id",
            "BL",
        ],
    ],
)
def test_add_subparser_run(args):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_run(subparsers)
    assert parser.parse_args(["run"] + args)


@pytest.mark.parametrize(
    "args",
    [
        ["my_dataset", "--pipeline", "pipeline1"],
        [
            "my_dataset",
            "--pipeline",
            "pipeline1",
            "--pipeline-version",
            "1.2.3",
            "--pipeline-step",
            "step1",
        ],
    ],
)
def test_add_subparser_track(args):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_track(subparsers)
    assert parser.parse_args(["track"] + args)


@pytest.mark.parametrize(
    "args",
    [
        ["my_dataset", "--pipeline", "pipeline1"],
        ["my_dataset", "--pipeline", "pipeline1", "--simulate"],
        [
            "my_dataset",
            "--pipeline",
            "pipeline1",
            "--pipeline-step",
            "step1",
        ],
    ],
)
def test_add_subparser_extract(args):
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    add_subparser_extract(subparsers)
    assert parser.parse_args(["extract"] + args)


@pytest.mark.parametrize(
    "args",
    [
        ["-h"],
        ["init", "-h"],
        ["init", "my_dataset"],
        ["init", "my_dataset", "--bids-source", "foo/bar"],
        ["doughnut", "my_dataset", "--regenerate"],
        ["reorg", "my_dataset", "--copy-files"],
        ["bidsify", "my_dataset", "--pipeline", "a_bids_pipeline"],
        ["run", "my_dataset", "--pipeline", "a_pipeline"],
        ["track", "my_dataset", "--pipeline", "another_pipeline"],
        [
            "extract",
            "my_dataset",
            "--pipeline",
            "extraction_pipeline",
        ],
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
