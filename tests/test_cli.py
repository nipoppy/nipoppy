"""Tests for the CLI."""

from pathlib import Path

from click.testing import CliRunner

from nipoppy.cli import cli
from nipoppy.env import ReturnCode

from .conftest import ATTR_TO_DPATH_MAP

runner = CliRunner()


def test_cli():
    result = runner.invoke(
        cli,
        ["-h"],
    )
    assert result.exit_code == ReturnCode.SUCCESS


def test_cli_invalid():
    result = runner.invoke(
        cli,
        ["--fake-arg"],
    )
    assert result.exit_code != ReturnCode.SUCCESS


def test_dep_params(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["init", dpath_root],
    )
    assert result.exit_code != ReturnCode.SUCCESS


def test_cli_init(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["init", "--dataset", dpath_root],
    )
    assert result.exit_code == ReturnCode.SUCCESS


def test_cli_status(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["status", "--dataset", dpath_root],
    )

    # No log file is created, since the status command does not create logs.
    pass

    # Expects missing path, since init command is not run.
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_doughnut(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(cli, ["doughnut", "--dataset", str(dpath_root)])

    # check that a logfile was created
    assert (
        len(list((dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob("doughnut/*.log")))
        == 1
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_reorg(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(cli, ["reorg", "--dataset", str(dpath_root)])

    # check that a logfile was created
    assert (
        len(
            list(
                (dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob("dicom_reorg/*.log")
            )
        )
        == 1
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_bidsify(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        [
            "bidsify",
            "--dataset",
            str(dpath_root),
            "--pipeline",
            "my_pipeline",
            "--pipeline-version",
            "1.0",
            "--pipeline-step",
            "step1",
        ],
        catch_exceptions=False,
    )

    # check that a logfile was created
    assert (
        len(
            list(
                (dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob(
                    "bids_conversion/my_pipeline-1.0/*.log"
                )
            )
        )
        == 1
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_run(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        [
            "run",
            "--dataset",
            str(dpath_root),
            "--pipeline",
            "my_pipeline",
            "--pipeline-version",
            "1.0",
        ],
        catch_exceptions=False,
    )

    # check that a logfile was created
    assert (
        len(
            list(
                (dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob(
                    "run/my_pipeline-1.0/*.log"
                )
            )
        )
        == 1
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_track(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        [
            "track",
            "--dataset",
            str(dpath_root),
            "--pipeline",
            "my_pipeline",
            "--pipeline-version",
            "1.0",
        ],
    )

    # check that a logfile was created
    assert (
        len(
            list(
                (dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob(
                    "track/my_pipeline-1.0/*.log"
                )
            )
        )
        == 1
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_extract(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        [
            "extract",
            "--dataset",
            str(dpath_root),
            "--pipeline",
            "my_pipeline",
            "--pipeline-version",
            "1.0",
        ],
    )

    # check that a logfile was created
    assert (
        len(
            list(
                (dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob(
                    "extract/my_pipeline-1.0/*.log"
                )
            )
        )
        == 1
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE
