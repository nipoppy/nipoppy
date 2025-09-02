"""Tests for the CLI."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import pytest_mock
from click.testing import CliRunner

from nipoppy.cli import exception_handler
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


def test_dep_params(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    nipoppy_study_path = tmp_path / "nipoppy_study"
    result = runner.invoke(
        cli,
        ["init", str(nipoppy_study_path)],
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
    tmp_path.joinpath("mocked_dir").mkdir(exist_ok=False)

    # Hack to inject the mocked directory into the command
    command = [arg.replace("[mocked_dir]", str(tmp_path)) for arg in command]

    if workflow:
        mocker.patch(f"{workflow}.run")
    assert_command_success(command)


def test_context_manager_no_exception(mocker):
    """Test that the context manager exits with SUCCESS when no exception occurs."""
    workflow = mocker.Mock()
    workflow.return_code = ReturnCode.SUCCESS
    mock_exit = mocker.patch("sys.exit")

    with exception_handler(workflow):
        pass

    mock_exit.assert_called_once_with(ReturnCode.SUCCESS)


@pytest.mark.parametrize(
    "exception, return_code, expected_return_code",
    [
        (SystemExit, ReturnCode.UNKNOWN_FAILURE, ReturnCode.UNKNOWN_FAILURE),
        (RuntimeError, ReturnCode.SUCCESS, ReturnCode.UNKNOWN_FAILURE),
        (RuntimeError, ReturnCode.PARTIAL_SUCCESS, ReturnCode.PARTIAL_SUCCESS),
        (ValueError, ReturnCode.UNKNOWN_FAILURE, ReturnCode.UNKNOWN_FAILURE),
    ],
)
def test_context_manager_exception(
    mocker, exception, return_code, expected_return_code
):
    """Test that the context manager handles exceptions correctly.

    SystemExit is treated as an unknown failure, while other exceptions
    are logged and set to UNKNOWN_FAILURE if the workflow exit code is still
    SUCCESS. Other exit codes are preserved.
    """
    workflow = mocker.Mock()
    workflow.return_code = return_code
    mock_exit = mocker.patch("sys.exit")

    with exception_handler(workflow):
        raise exception()

    assert workflow.return_code == expected_return_code
    mock_exit.assert_called_once_with(expected_return_code)
