"""Tests for the CLI."""

from __future__ import annotations

import logging
import shlex
from pathlib import Path

import pytest
import pytest_mock
from click.testing import CliRunner

from nipoppy.cli.cli import cli
from nipoppy.env import ReturnCode
from tests.conftest import PASSWORD_FILE

runner = CliRunner()


def assert_command_success(args):
    """Assert that the CLI command runs successfully."""
    result = runner.invoke(cli, args, catch_exceptions=False)
    assert (
        result.exit_code == ReturnCode.SUCCESS
    ), f"Command failed: {args}\n{result.output}"


@pytest.mark.parametrize("args", [["--invalid-arg"], ["invalid_command"]])
def test_cli_invalid(args):
    """Test that a fake command does not exist."""
    result = runner.invoke(cli, args, catch_exceptions=False)
    assert (
        result.exit_code == ReturnCode.INVALID_COMMAND
    ), f"Expected invalid command exit code for: {args}\n{result.output}"


@pytest.mark.parametrize(
    "command,workflow,expected_warning",
    [
        (
            ["init", "[tmp_path]/nipoppy_study"],
            "nipoppy.workflows.dataset_init.InitWorkflow",
            "Giving the dataset path without --dataset is deprecated",
        ),
        (
            [
                "process",
                "--dataset",
                "[tmp_path]/nipoppy_study",
                "--pipeline",
                "fake_pipeline",
                "--write-list",
                "[tmp_path]/subcohort.txt",
            ],
            "nipoppy.workflows.runner.PipelineRunner",
            (
                "The --write-list option is deprecated and will be removed in a future "
                "version. Use --write-subcohort instead."
            ),
        ),
    ],
)
def test_dep_params(
    command: str,
    workflow: str,
    expected_warning,
    tmp_path: Path,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    mocker.patch(f"{workflow}.run")
    command = shlex.join(command).replace("[tmp_path]", str(tmp_path))
    result = runner.invoke(cli, command, catch_exceptions=False)

    assert any(
        [
            expected_warning in record.message and record.levelno == logging.WARNING
            for record in caplog.records
        ]
    )
    assert result.exit_code == ReturnCode.SUCCESS


@pytest.mark.parametrize("command", ["doughnut", "run", "track"])
def test_cli_deprecations(command, caplog: pytest.LogCaptureFixture):
    assert_command_success(f"{command} -h")
    assert any(
        [
            (record.levelno == logging.WARNING and "is deprecated" in record.message)
            for record in caplog.records
        ]
    )


@pytest.mark.parametrize("trogon_installed", [True, False])
def test_cli_gui_visibility(monkeypatch, trogon_installed):
    import importlib
    import sys

    if not trogon_installed:
        monkeypatch.setitem(sys.modules, "trogon", None)

    import nipoppy.cli.cli as cli

    importlib.reload(cli)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["gui", "--help"])

    assert ("Open the Nipoppy terminal GUI. " in result.output) == trogon_installed


@pytest.mark.parametrize(
    (
        "command",
        "workflow",
    ),
    [
        (
            ["--help"],
            None,
        ),
        (
            [
                "init",
                "--dataset",
                "[mocked_dir]",
            ],
            "nipoppy.workflows.dataset_init.InitWorkflow",
        ),
        (
            [
                "track-curation",
                "--dataset",
                "[mocked_dir]",
            ],
            "nipoppy.workflows.track_curation.TrackCurationWorkflow",
        ),
        (
            [
                "reorg",
                "--dataset",
                "[mocked_dir]",
            ],
            "nipoppy.workflows.dicom_reorg.DicomReorgWorkflow",
        ),
        (
            [
                "bidsify",
                "--dataset",
                "[mocked_dir]",
                "--pipeline",
                "my_pipeline",
                "--pipeline-version",
                "1.0",
                "--pipeline-step",
                "step1",
            ],
            "nipoppy.workflows.bids_conversion.BidsConversionRunner",
        ),
        (
            [
                "process",
                "--dataset",
                "[mocked_dir]",
                "--pipeline",
                "my_pipeline",
                "--pipeline-version",
                "1.0",
            ],
            "nipoppy.workflows.runner.PipelineRunner",
        ),
        (
            [
                "track-processing",
                "--dataset",
                "[mocked_dir]",
                "--pipeline",
                "my_pipeline",
                "--pipeline-version",
                "1.0",
            ],
            "nipoppy.workflows.tracker.PipelineTracker",
        ),
        (
            [
                "extract",
                "--dataset",
                "[mocked_dir]",
                "--pipeline",
                "my_pipeline",
                "--pipeline-version",
                "1.0",
            ],
            "nipoppy.workflows.extractor.ExtractionRunner",
        ),
        (
            [
                "status",
                "--dataset",
                "[mocked_dir]",
            ],
            "nipoppy.workflows.dataset_status.StatusWorkflow",
        ),
        (
            [
                "pipeline",
                "search",
                "mriqc",
            ],
            "nipoppy.workflows.pipeline_store.search.PipelineSearchWorkflow",
        ),
        (
            [
                "pipeline",
                "create",
                "--type",
                "processing",
                "[mocked_dir]",
            ],
            "nipoppy.workflows.pipeline_store.create.PipelineCreateWorkflow",
        ),
        (
            [
                "pipeline",
                "install",
                "--dataset",
                "[mocked_dir]",
                "zenodo.123456",
            ],
            "nipoppy.workflows.pipeline_store.install.PipelineInstallWorkflow",
        ),
        (
            [
                "pipeline",
                "list",
                "--dataset",
                "[mocked_dir]",
            ],
            "nipoppy.workflows.pipeline_store.list.PipelineListWorkflow",
        ),
        (
            ["pipeline", "validate", "[mocked_dir]"],
            "nipoppy.workflows.pipeline_store.validate.PipelineValidateWorkflow",
        ),
        (
            [
                "pipeline",
                "upload",
                "mocked.zip",
                "--zenodo-id",
                "zenodo.123456",
                "--password-file",
                str(PASSWORD_FILE),
            ],
            "nipoppy.workflows.pipeline_store.upload.ZenodoUploadWorkflow",
        ),
    ],
)
def test_cli_command(
    command: list[str],
    workflow: str | None,
    mocker: pytest_mock.MockerFixture,
    tmp_path: Path,
):
    """Test that the CLI commands run the expected workflows."""
    # Required for some Click commands to work properly
    mocked_dir = tmp_path.joinpath("mocked_dir")
    mocked_dir.mkdir(exist_ok=False)

    # Hack to inject the mocked directory into the command
    command = [arg.replace("[mocked_dir]", str(mocked_dir)) for arg in command]

    if workflow:
        mocker.patch(f"{workflow}.run")
    assert_command_success(command)
