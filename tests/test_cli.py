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
    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_init(tmp_path: Path):
    result = runner.invoke(
        cli,
        ["init", "--dataset", str(tmp_path / "my_dataset")],
    )
    assert result.exit_code == ReturnCode.SUCCESS


def test_cli_init_dir_exists(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    dpath_root.joinpath("dir_exists").mkdir(parents=True, exist_ok=True)

    result = runner.invoke(
        cli,
        ["init", "--dataset", str(dpath_root)],
    )

    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_doughnut(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    result = runner.invoke(cli, ["doughnut", "--dataset", str(dpath_root)])

    # check that a logfile was created
    assert (
        len(list((dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob("doughnut/*.log")))
        == 1
    )

    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_dicom_reorg(tmp_path: Path):
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

    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_bids_conversion(tmp_path: Path):
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

    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_pipeline_run(tmp_path: Path):
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

    assert result.exit_code == ReturnCode.UNKOWN_FAILURE


def test_cli_pipeline_track(tmp_path: Path):
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

    assert result.exit_code == ReturnCode.UNKOWN_FAILURE
