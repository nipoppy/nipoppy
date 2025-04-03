"""Tests for the CLI."""

import logging
from pathlib import Path

import pytest
from click.testing import CliRunner

from nipoppy.cli import cli
from nipoppy.env import ReturnCode

from .conftest import ATTR_TO_DPATH_MAP

runner = CliRunner()


def test_cli():
    result = runner.invoke(
        cli,
        ["-h"],
        catch_exceptions=False,
    )
    assert result.exit_code == ReturnCode.SUCCESS


def test_cli_invalid():
    result = runner.invoke(
        cli,
        ["--fake-arg"],
        catch_exceptions=False,
    )
    assert result.exit_code != ReturnCode.SUCCESS


def test_dep_params(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["init", str(dpath_root)],
        catch_exceptions=False,
    )

    assert any(
        [
            "Giving the dataset path without --dataset is deprecated" in record.message
            and record.levelno == logging.WARNING
            for record in caplog.records
        ]
    )
    assert result.exit_code == ReturnCode.SUCCESS


def test_cli_init(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["init", "--dataset", dpath_root],
        catch_exceptions=False,
    )
    assert result.exit_code == ReturnCode.SUCCESS


def test_cli_status(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["status", "--dataset", dpath_root],
        catch_exceptions=False,
    )

    # No log file is created, since the status command does not create logs.
    pass

    # Expects missing path, since init command is not run.
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


def test_cli_doughnut(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli, ["doughnut", "--dataset", dpath_root], catch_exceptions=False
    )

    # check that a logfile was created
    assert (
        len(list((dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob("doughnut/*.log")))
        == 1
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


def test_cli_reorg(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["reorg", "--dataset", dpath_root],
        catch_exceptions=False,
    )

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
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


def test_cli_bidsify(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        [
            "bidsify",
            "--dataset",
            dpath_root,
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
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


def test_cli_run(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        [
            "run",
            "--dataset",
            dpath_root,
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
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


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
        catch_exceptions=False,
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
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


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
        catch_exceptions=False,
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
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


def test_cli_pipeline_list(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["pipeline", "list", "--dataset", dpath_root],
    )

    # Expects missing path, since init command is not run.
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


def test_cli_pipeline_validate(tmp_path: Path):
    dpath_pipeline = tmp_path / "pipeline"
    dpath_pipeline.mkdir()
    result = runner.invoke(
        cli,
        ["pipeline", "validate", str(dpath_pipeline)],
        catch_exceptions=False,
    )

    # Expects missing path, since init command is not run.
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE
