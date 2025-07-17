"""Tests for the CLI."""

import logging
from pathlib import Path

import pytest
from click.testing import CliRunner

from nipoppy.cli import cli
from nipoppy.env import ReturnCode

from .conftest import ATTR_TO_DPATH_MAP, PASSWORD_FILE

runner = CliRunner()


def test_cli():
    result = runner.invoke(
        cli,
        ["-h"],
        catch_exceptions=False,
    )
    assert result.exit_code == ReturnCode.SUCCESS


@pytest.mark.parametrize("args", [["--fake-arg"], ["fake_command"]])
def test_cli_invalid(args):
    result = runner.invoke(cli, args, catch_exceptions=False)
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


def test_cli_track_curation(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(
        cli,
        ["track-curation", "--dataset", str(dpath_root)],
        catch_exceptions=False,
    )

    # check that a logfile was created
    assert (
        len(
            list(
                (dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob(
                    "track_curation/*.log"
                )
            )
        )
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
            "process",
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
                    "process/my_pipeline-1.0/*.log"
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
            "track-processing",
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
                    "track_processing/my_pipeline-1.0/*.log"
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


def test_cli_pipeline_upload():
    result = runner.invoke(
        cli,
        [
            "pipeline",
            "upload",
            "tests/data/zenodo.zip",
            "--zenodo-id",
            "zenodo.123456",
            "--password-file",
            PASSWORD_FILE,
        ],
        catch_exceptions=False,
    )

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


@pytest.mark.parametrize("from_zenodo", [True, False])
def test_cli_pipeline_install(from_zenodo, tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    dpath_pipeline = tmp_path / "pipeline"
    dpath_pipeline.mkdir()

    source = "zenodo.123456" if from_zenodo else str(dpath_pipeline)

    result = runner.invoke(
        cli,
        ["pipeline", "install", "--dataset", str(dpath_root), source],
        catch_exceptions=False,
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

    # Expect non-zero return code, because nipoppy init was not run.
    assert result.exit_code == ReturnCode.UNKNOWN_FAILURE


def test_cli_pipeline_search():
    result = runner.invoke(
        cli,
        ["pipeline", "search", "mriqc"],
        catch_exceptions=False,
    )
    assert result.exit_code == ReturnCode.SUCCESS


def test_cli_pipeline_create(tmp_path: Path):
    result = runner.invoke(
        cli,
        [
            "pipeline",
            "create",
            "--type",
            "processing",
            str(tmp_path.joinpath("new_pipeline_bundle")),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == ReturnCode.SUCCESS


@pytest.mark.parametrize("command", ["doughnut", "run", "track"])
def test_cli_deprecations(command, caplog: pytest.LogCaptureFixture):
    runner.invoke(cli, [command, "-h"], catch_exceptions=False)
    assert any(
        [
            (record.levelno == logging.WARNING and "is deprecated" in record.message)
            for record in caplog.records
        ]
    )


def test_cli_tui():
    """Verify that the TUI `gui` command is registered.

    TODO: It would be better to test the Trogon app directly, but we would have to
    invoke Trogon directly, without the tui decorator.
    """
    result = runner.invoke(
        cli,
        ["gui", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == ReturnCode.SUCCESS


@pytest.mark.parametrize("trogon_installed", [True, False])
def test_cli_gui_visibility(monkeypatch, trogon_installed):
    import importlib
    import sys

    if not trogon_installed:
        monkeypatch.setitem(sys.modules, "trogon", None)

    import nipoppy.cli as cli

    importlib.reload(cli)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["gui", "--help"])

    assert ("Open the Nipoppy terminal GUI. " in result.output) == trogon_installed
