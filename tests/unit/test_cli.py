"""Tests for the CLI."""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import re
import shlex
from pathlib import Path

import pytest
import pytest_mock
import rich_click as click
from click.testing import CliRunner

from nipoppy.cli import (
    BUG_REPORT_URL,
    DISCORD_URL,
    OrderedAliasedGroup,
    exception_handler,
)
from nipoppy.cli.cli import cli
from nipoppy.cli.options import (
    DOTENV_PATHS_VAR,
    DotenvFileManager,
    _load_dotenv_files,
    dataset_option,
)
from nipoppy.exceptions import JSONError, NipoppyError, ReturnCode
from tests.conftest import PASSWORD_FILE, list_cli_commands

runner = CliRunner()

RE_ANSI = re.compile(r"\033\[[;?0-9]*[a-zA-Z]")

# tuple of command/subcommands -> (module path, workflow class name)
COMMAND_WORKFLOW_MAP = {
    "init": ("nipoppy.workflows.dataset_init", "InitWorkflow"),
    "track-curation": ("nipoppy.workflows.track_curation", "TrackCurationWorkflow"),
    "reorg": ("nipoppy.workflows.dicom_reorg", "DicomReorgWorkflow"),
    "bidsify": ("nipoppy.workflows.bids_conversion", "BIDSificationRunner"),
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

DEFAULT_VALUE_DUMMY_CLI = "default"


@pytest.fixture
def dummy_cli():
    @click.group(cls=OrderedAliasedGroup)
    @_load_dotenv_files
    def cli():
        pass

    @cli.command()
    @click.option("--test-param", default=DEFAULT_VALUE_DUMMY_CLI, envvar="TEST_PARAM")
    def subcommand_without_dataset(**params):
        print(params["test_param"])

    @cli.command()
    @click.option("--test-param", default=DEFAULT_VALUE_DUMMY_CLI, envvar="TEST_PARAM")
    @dataset_option
    def subcommand_with_dataset(**params):
        print(params["test_param"])

    @cli.command()
    @dataset_option
    @click.pass_context
    def subcommand_double_load(ctx: click.Context, **params):
        dotenv_manager = ctx.ensure_object(DotenvFileManager)
        dotenv_manager.load()

    return cli


def _assert_command_success(args):
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
            "nipoppy.workflows.processing_runner.ProcessingRunner",
            (
                "The --write-list option is deprecated and will be removed in a future "
                "version. Use --write-subcohort instead."
            ),
        ),
    ],
)
@pytest.mark.no_xdist
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


@pytest.mark.no_xdist
@pytest.mark.parametrize("command", ["doughnut", "run", "track"])
def test_cli_deprecations(command, caplog: pytest.LogCaptureFixture):
    _assert_command_success(f"{command} -h")
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
                "search",
                "--password-file",
                str(PASSWORD_FILE),
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
                "install",
                "--dataset",
                "[mocked_dir]",
                "zenodo.123456",
                "--password-file",
                str(PASSWORD_FILE),
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
    _assert_command_success(command)


def test_context_manager_no_exception(mocker):
    """Test that the context manager exits with SUCCESS when no exception occurs."""
    workflow = mocker.Mock()
    workflow.return_code = ReturnCode.SUCCESS
    mock_exit = mocker.patch("sys.exit")

    with exception_handler(workflow):
        pass

    mock_exit.assert_called_once_with(ReturnCode.SUCCESS)


@pytest.mark.parametrize(
    "return_code, expected_return_code",
    [
        (None, ReturnCode.UNKNOWN_FAILURE),
        (ReturnCode.UNKNOWN_FAILURE, ReturnCode.UNKNOWN_FAILURE),
        (ReturnCode.INVALID_COMMAND, ReturnCode.INVALID_COMMAND),
    ],
)
def test_context_manager_system_exit_exception(
    mocker: pytest_mock.MockerFixture, return_code, expected_return_code, caplog
):
    """Test that the context manager handles exceptions correctly.

    SystemExit should set the workflow return code to the
    exception's code. Other exceptions should set it to UNKNOWN_FAILURE.
    """
    # Prevent sys.exit from actually exiting the test runner
    mock_exit = mocker.patch("sys.exit")

    workflow = mocker.Mock()
    with exception_handler(workflow):
        if return_code is None:
            raise SystemExit
        else:
            raise SystemExit(return_code)

    assert workflow.return_code == expected_return_code
    mock_exit.assert_called_once_with(expected_return_code)


class MyCustomException(NipoppyError):
    code = 999


@pytest.mark.parametrize(
    "exception",
    [
        NipoppyError,
        MyCustomException,
    ],
)
def test_context_manager_nipoppy_exception(
    mocker: pytest_mock.MockerFixture, exception
):
    """Test that the context manager handles exceptions correctly.

    NipoppyError and its subclasses should set the workflow return code to the
    exception's code. Other exceptions should set it to UNKNOWN_FAILURE.
    """
    # Prevent sys.exit from actually exiting the test runner
    mock_exit = mocker.patch("sys.exit")

    workflow = mocker.Mock()
    with exception_handler(workflow):
        raise exception

    assert workflow.return_code == exception.code
    mock_exit.assert_called_once_with(exception.code)


@pytest.mark.parametrize("hint", ["", "This is a hint."])
def test_context_manager_nipoppy_exception_logs_custom_hint(
    hint, mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Known NipoppyError should emit custom hint when provided."""
    mocker.patch("sys.exit")

    workflow = mocker.Mock()
    with exception_handler(workflow):
        raise NipoppyError("Invalid project config", hint=hint)

    assert any(
        "Troubleshooting:" in record.message and hint in record.message
        for record in caplog.records
    )


def test_context_manager_nipoppy_exception_logs_default_hint(
    mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Known NipoppyError should emit default hint when none provided."""
    mocker.patch("sys.exit")

    workflow = mocker.Mock()
    default_hint = "This is a default hint."
    with exception_handler(workflow):
        e = NipoppyError("Invalid project config", hint=None)
        e.default_hint = default_hint
        raise e

    assert any(
        f"Troubleshooting: {default_hint}" in record.message
        for record in caplog.records
    )


def test_context_manager_json_error(
    mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Test that JSONError includes the file path in the error message."""
    mocker.patch("sys.exit")

    workflow = mocker.Mock()
    fpath = "invalid.json"
    with exception_handler(workflow):
        raise JSONError(
            json.JSONDecodeError("Invalid JSON", "{}", 10),
            fpath=Path(fpath),
        )
    assert any(
        f"Invalid JSON: {fpath}: line 1 column 11 (char 10)" in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "return_code", [(None), (ReturnCode.UNKNOWN_FAILURE), (ReturnCode.INVALID_COMMAND)]
)
@pytest.mark.parametrize("exception", [Exception, RuntimeError])
def test_context_manager_unknown_exception(
    mocker: pytest_mock.MockerFixture,
    exception,
    return_code,
    caplog: pytest.LogCaptureFixture,
):
    """Test that the context manager handles exceptions correctly.

    Unknown exception (Exception) should always set the return code to UNKNOWN_FAILURE.
    """
    # Prevent sys.exit from actually exiting the test runner
    mock_exit = mocker.patch("sys.exit")

    workflow = mocker.Mock()
    with exception_handler(workflow):
        if return_code is None:
            raise exception
        else:
            raise exception(code=return_code)

    # Exit code is always set to UNKNOWN_FAILURE for unknown exceptions
    assert workflow.return_code == ReturnCode.UNKNOWN_FAILURE
    mock_exit.assert_called_once_with(ReturnCode.UNKNOWN_FAILURE)
    assert any(BUG_REPORT_URL in record.message for record in caplog.records)
    assert any(DISCORD_URL in record.message for record in caplog.records)


def test_context_manager_pydantic_failed_validation(
    mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Test that the context manager handles pydantic ValidationError correctly."""
    from pydantic import BaseModel

    # Prevent sys.exit from actually exiting the test runner
    mock_exit = mocker.patch("sys.exit")

    workflow = mocker.Mock()

    class MockedModel(BaseModel):
        field: int

    with exception_handler(workflow):
        MockedModel(field="invalid")  # will raise ValidationError

    assert workflow.return_code == ReturnCode.INVALID_CONFIG
    mock_exit.assert_called_once_with(ReturnCode.INVALID_CONFIG)
    assert any(
        "Troubleshooting:" in record.message
        and "Review your configuration fields and value types" in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize("command", list_cli_commands(cli))
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
    list_cli_commands(cli, include_hidden=False, include_group=False),
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


@pytest.mark.parametrize(
    "subcommand,dotenv_global_content,dotenv_local_content,env_vars,cli_args,expected_parsed_param",  # noqa: E501
    [
        (
            "subcommand-with-dataset",
            "TEST_PARAM='dotenv_global'",
            "TEST_PARAM='dotenv_local'",
            {"TEST_PARAM": "env_var"},
            ["--test-param", "cli_arg"],
            "cli_arg",
        ),
        (
            "subcommand-with-dataset",
            "TEST_PARAM='dotenv_global'",
            "TEST_PARAM='dotenv_local'",
            {"TEST_PARAM": "env_var"},
            [],
            "env_var",
        ),
        (
            "subcommand-with-dataset",
            "TEST_PARAM='dotenv_global'",
            "TEST_PARAM='dotenv_local'",
            {},
            [],
            "dotenv_local",
        ),
        (
            "subcommand-with-dataset",
            "TEST_PARAM='dotenv_global'",
            "",
            {},
            [],
            "dotenv_global",
        ),
        (
            "subcommand-with-dataset",
            "TEST_PARAM='dotenv_global'",
            None,
            {},
            [],
            "dotenv_global",
        ),
        ("subcommand-with-dataset", "", None, {}, [], DEFAULT_VALUE_DUMMY_CLI),
        ("subcommand-with-dataset", None, None, {}, [], DEFAULT_VALUE_DUMMY_CLI),
        (
            "subcommand-without-dataset",
            "TEST_PARAM='dotenv_global'",
            "TEST_PARAM='dotenv_local'",  # ignored
            {},
            [],
            "dotenv_global",
        ),
    ],
)
def test_param_source_priority(
    dummy_cli: click.Group,
    subcommand: str,
    dotenv_global_content,
    dotenv_local_content,
    env_vars,
    cli_args,
    expected_parsed_param: str,
    tmp_path: Path,
    restore_environment,
):
    dpath_root = tmp_path / "nipoppy_root"

    fpath_dotenv_global = tmp_path / "dotenv_global.env"
    fpath_dotenv_local = dpath_root / "dotenv_local.env"
    fpath_dotenv_local_template = "[[NIPOPPY_DPATH_ROOT]]/dotenv_local.env"

    if dotenv_global_content is not None:
        fpath_dotenv_global.write_text(dotenv_global_content)

    if dotenv_local_content is not None:
        fpath_dotenv_local.parent.mkdir(parents=True, exist_ok=True)
        fpath_dotenv_local.write_text(dotenv_local_content)

    # local dotenv has higher priority than global dotenv
    env_vars[DOTENV_PATHS_VAR] = os.pathsep.join(
        [str(fpath_dotenv_local_template), str(fpath_dotenv_global)]
    )

    if subcommand == "subcommand-with-dataset":
        cli_args += ["--dataset", str(dpath_root)]
    results = runner.invoke(
        dummy_cli, [subcommand] + cli_args, env=env_vars, catch_exceptions=False
    )

    # get the last printed line which should be the parsed parameter value
    parsed_param = results.stdout.split()[-1].strip()

    assert parsed_param == expected_parsed_param


def test_error_on_double_load_dotenv(dummy_cli: click.Group):
    with pytest.raises(
        RuntimeError, match="Environment variables have already been loaded"
    ):
        runner.invoke(dummy_cli, ["subcommand-double-load"], catch_exceptions=False)


@pytest.mark.parametrize(
    "command_name", [None] + list_cli_commands(cli, include_hidden=False)
)
def test_all_groups_have_dotenv_decorator(command_name: str | None):
    command = cli
    if command_name is not None:
        for command_component in command_name.split(" "):
            command = command.get_command(None, command_component)

    if isinstance(command, click.Group):
        callback = command.callback
        source = inspect.getsource(callback)
        assert (
            "_load_dotenv_files" in source
        ), f"Group command '{command_name}' is missing the @_load_dotenv_files decorator."  # noqa: E501


def test_dataset_arg_and_option_not_allowed(tmp_path: Path):
    command = [
        "init",
        f"{tmp_path}/nipoppy_study",
        "--dataset",
        f"{tmp_path}/nipoppy_study",
    ]
    result = runner.invoke(cli, command, catch_exceptions=False)

    assert (
        # need to take into account ANSI escape codes and terminal max width
        "Cannot provide both the dataset argument and the --dataset option."
        in RE_ANSI.sub("", result.output)
    )

    assert result.exit_code == ReturnCode.INVALID_COMMAND


@pytest.mark.parametrize(
    "command_name",
    list_cli_commands(cli, include_hidden=False, include_group=False),
)
def test_cli_show_envvar(command_name: str):
    # get Click Command object
    command = cli
    for command_component in command_name.split(" "):
        command = command.get_command(None, command_component)

    for param in command.params:
        if param.envvar is not None:
            assert param.show_envvar, (
                f"Parameter '{param.name}' in subcommand '{command_name}' has envvar "
                f"'{param.envvar}' but show_envvar is False. Set show_envvar to True "
                f"to display the env var in the help message."
            )
