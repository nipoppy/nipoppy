"""Tests for the CLI."""

from __future__ import annotations

import importlib
import inspect
import logging
import shlex
from pathlib import Path

import click
import pytest
import pytest_mock
from click.testing import CliRunner

from nipoppy.cli import exception_handler
from nipoppy.cli.cli import cli
from nipoppy.env import ReturnCode
from tests.conftest import PASSWORD_FILE

runner = CliRunner()

# tuple of command/subcommands -> (module path, workflow class name)
COMMAND_WORKFLOW_MAP = {
    "init": ("nipoppy.workflows.dataset_init", "InitWorkflow"),
    "track-curation": ("nipoppy.workflows.track_curation", "TrackCurationWorkflow"),
    "reorg": ("nipoppy.workflows.dicom_reorg", "DicomReorgWorkflow"),
    "bidsify": ("nipoppy.workflows.bids_conversion", "BidsConversionRunner"),
    "process": ("nipoppy.workflows.processing_runner", "ProcessingRunner"),
    "track-processing": ("nipoppy.workflows.tracker", "PipelineTracker"),
    "extract": ("nipoppy.workflows.extractor", "ExtractionRunner"),
    "status": ("nipoppy.workflows.dataset_status", "StatusWorkflow"),
    "pipeline search": (
        "nipoppy.workflows.pipeline_store.search",
        "PipelineSearchWorkflow",
    ),
    "pipeline create": (
        "nipoppy.workflows.pipeline_store.create",
        "PipelineCreateWorkflow",
    ),
    "pipeline install": (
        "nipoppy.workflows.pipeline_store.install",
        "PipelineInstallWorkflow",
    ),
    "pipeline list": (
        "nipoppy.workflows.pipeline_store.list",
        "PipelineListWorkflow",
    ),
    "pipeline validate": (
        "nipoppy.workflows.pipeline_store.validate",
        "PipelineValidateWorkflow",
    ),
    "pipeline upload": (
        "nipoppy.workflows.pipeline_store.upload",
        "PipelineUploadWorkflow",
    ),
}


def assert_command_success(args):
    """Assert that the CLI command runs successfully."""
    result = runner.invoke(cli, args, catch_exceptions=False)
    assert (
        result.exit_code == ReturnCode.SUCCESS
    ), f"Command failed: {args}\n{result.output}"


def list_commands(group: click.Group, prefix=""):
    commands = []
    for name, cmd in group.commands.items():
        full_name = f"{prefix}{name}"
        commands.append(full_name)

        # If the command is itself a group, recurse
        if isinstance(cmd, click.Group):
            commands.extend(list_commands(cmd, prefix=f"{full_name} "))
    return commands


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
            "nipoppy.workflows.processing_runner.ProcessingRunner",
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
            "nipoppy.workflows.bids_conversion.BIDSificationRunner",
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
            "nipoppy.workflows.processing_runner.ProcessingRunner",
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
            "nipoppy.workflows.pipeline_store.upload.PipelineUploadWorkflow",
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


@pytest.mark.parametrize("command", list_commands(cli))
def test_no_duplicated_flag(
    command: str,
    recwarn: pytest.WarningsRecorder,
):
    """Test that no duplicated flags are present in the CLI commands."""
    runner.invoke(cli, f"{command} --help", catch_exceptions=False)
    assert not any(
        "Remove its duplicate as parameters should be unique." in str(warning.message)
        for warning in recwarn
    )


@pytest.mark.parametrize(
    "command_name",
    [command for command in list_commands(cli) if command not in ("gui", "pipeline")],
)
def test_cli_params_match_workflows(command_name):
    ignored_params = {
        "name",  # not exposed to CLI
        "zenodo_api",  # instantiated by the CLI from other params
        "dpath_pipeline",  # positional arg in CLI
    }

    # get Click Command object
    module_path, workflow_name = COMMAND_WORKFLOW_MAP[command_name]
    command = cli
    for command_component in command_name.split(" "):
        command = command.get_command(None, command_component)

    # get workflow class
    module = importlib.import_module(module_path)
    workflow_class = getattr(module, workflow_name)

    params_workflow = {
        p.name
        for p in inspect.signature(workflow_class.__init__).parameters.values()
        if (
            p.name != "self"
            and not p.name.startswith("_")
            and p.name not in ignored_params
        )
    }
    params_command = {p.name for p in command.params}

    missing_params = params_workflow - params_command
    assert len(missing_params) == 0, (
        f"Command '{command_name}' is missing params {missing_params}"
        f" expected by {workflow_name}"
    )
