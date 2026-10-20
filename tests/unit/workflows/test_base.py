"""Tests for the BaseWorkflow class."""

import json
import logging
import subprocess
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.env import BUG_REPORT_URL, DISCORD_URL
from nipoppy.exceptions import JSONError, NipoppyError, ReturnCode
from nipoppy.workflows.base import (
    BaseWorkflow,
    LogPrefix,
    _handle_exception,
    _log_command,
    _run_command,
)
from nipoppy.zenodo_api import ZenodoAPIError


@pytest.fixture()
def workflow():
    class DummyWorkflow(BaseWorkflow):
        def run_main(self):
            pass

    workflow = DummyWorkflow(name="my_workflow")

    return workflow


def test_abstract_class():
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseWorkflow(None, None)


def test_init(workflow: BaseWorkflow):
    assert workflow.name == "my_workflow"
    assert workflow.return_code == 0


@pytest.mark.parametrize("command", ["echo x", "echo y"])
@pytest.mark.no_xdist
def test_log_command(command, caplog: pytest.LogCaptureFixture):
    _log_command(command)
    assert caplog.records
    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    assert record.message.startswith(LogPrefix.RUN)
    assert command in record.message


def test_run(workflow: BaseWorkflow):
    assert workflow.run() is None


@pytest.mark.parametrize(
    "return_code, expected_return_code",
    [
        (None, ReturnCode.UNKNOWN_FAILURE),
        (ReturnCode.UNKNOWN_FAILURE, ReturnCode.UNKNOWN_FAILURE),
        (ReturnCode.INVALID_ARGUMENT, ReturnCode.INVALID_ARGUMENT),
    ],
)
def test_handle_exception_system_exit_exception(
    mocker: pytest_mock.MockerFixture, return_code, expected_return_code, caplog
):
    """Test that the context manager handles exceptions correctly.

    SystemExit should set the workflow return code to the
    exception's code. Other exceptions should set it to UNKNOWN_FAILURE.
    """
    workflow = mocker.Mock()
    with pytest.raises(SystemExit), _handle_exception(workflow):
        if return_code is None:
            raise SystemExit
        else:
            raise SystemExit(return_code)

    assert workflow.return_code == expected_return_code


class MyCustomException(NipoppyError):
    code = 999


@pytest.mark.parametrize(
    "exception,return_code",
    [
        (NipoppyError, NipoppyError.code),
        (ZenodoAPIError, ReturnCode.KNOWN_FAILURE),
        (MyCustomException, MyCustomException.code),
    ],
)
def test_handle_exception_nipoppy_exception(
    mocker: pytest_mock.MockerFixture, exception: Exception, return_code: int
):
    """Test that the context manager handles exceptions correctly.

    NipoppyError and its subclasses should set the workflow return code to the
    exception's code. Other exceptions should set it to UNKNOWN_FAILURE.
    """
    workflow = mocker.Mock()
    with pytest.raises(exception), _handle_exception(workflow):
        raise exception

    assert workflow.return_code == return_code


@pytest.mark.parametrize("hint", ["", "This is a hint."])
def test_handle_exception_nipoppy_exception_logs_custom_hint(
    hint, mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Known NipoppyError should emit custom hint when provided."""
    workflow = mocker.Mock()
    with pytest.raises(NipoppyError), _handle_exception(workflow):
        raise NipoppyError("Invalid project config", hint=hint)

    assert any(
        "Troubleshooting:" in record.message and hint in record.message
        for record in caplog.records
    )


def test_handle_exception_nipoppy_exception_logs_default_hint(
    mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Known NipoppyError should emit default hint when none provided."""
    workflow = mocker.Mock()
    default_hint = "This is a default hint."
    with pytest.raises(NipoppyError), _handle_exception(workflow):
        e = NipoppyError("Invalid project config", hint=None)
        e.default_hint = default_hint
        raise e

    assert any(
        f"Troubleshooting: {default_hint}" in record.message
        for record in caplog.records
    )


def test_handle_exception_json_error(
    mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Test that JSONError includes the file path in the error message."""
    workflow = mocker.Mock()
    fpath = "invalid.json"
    with pytest.raises(JSONError), _handle_exception(workflow):
        raise JSONError(
            json.JSONDecodeError("Invalid JSON", "{}", 10),
            fpath=Path(fpath),
        )
    assert any(
        f"Invalid JSON: {fpath}: line 1 column 11 (char 10)" in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "return_code", [(None), (ReturnCode.UNKNOWN_FAILURE), (ReturnCode.INVALID_ARGUMENT)]
)
@pytest.mark.parametrize("exception", [Exception, RuntimeError])
def test_handle_exception_unknown_exception(
    mocker: pytest_mock.MockerFixture,
    exception,
    return_code,
    caplog: pytest.LogCaptureFixture,
):
    """Test that the context manager handles exceptions correctly.

    Unknown exception (Exception) should always set the return code to UNKNOWN_FAILURE.
    """
    workflow = mocker.Mock()
    with pytest.raises(Exception), _handle_exception(workflow):
        if return_code is None:
            raise exception
        else:
            raise exception(code=return_code)

    # Exit code is always set to UNKNOWN_FAILURE for unknown exceptions
    assert workflow.return_code == ReturnCode.UNKNOWN_FAILURE
    assert any(BUG_REPORT_URL in record.message for record in caplog.records)
    assert any(DISCORD_URL in record.message for record in caplog.records)


def test_handle_exception_pydantic_failed_validation(
    mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    """Test that the context manager handles pydantic ValidationError correctly."""
    from pydantic import BaseModel, ValidationError

    workflow = mocker.Mock()

    class MockedModel(BaseModel):
        field: int

    with pytest.raises(ValidationError), _handle_exception(workflow):
        MockedModel(field="invalid")  # will raise ValidationError

    assert workflow.return_code == ReturnCode.INVALID_CONFIG
    assert any(
        "Troubleshooting:" in record.message
        and "Review your configuration fields and value types" in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize("method", ["run_setup", "run_main", "run_cleanup"])
def test_run_exception(
    workflow: BaseWorkflow, method: str, mocker: pytest_mock.MockerFixture
):
    """Test that an exception raised during the workflow sets the return code."""
    mocker.patch.object(workflow, method, side_effect=MyCustomException)

    with pytest.raises(MyCustomException):
        workflow.run()

    assert workflow.return_code == MyCustomException.code


# TODO we might want to move these tests to a separate test file or reorganize them
# Previously, were using the BaseWorkflow.run_command method, which has been extracted
# to a standalone function. The tests have been adapted accordingly.
@pytest.mark.no_xdist
def test_log_command_no_markup(caplog: pytest.LogCaptureFixture):
    # message with closing tag
    message = "[/]"

    # this should not raise a rich markup error
    _run_command(["echo", message])
    assert message in caplog.text


def test_run_command(tmp_path: Path):
    fpath = tmp_path / "test.txt"
    process = _run_command(["touch", fpath])
    assert process.returncode == 0
    assert fpath.exists()


def test_run_command_single_string(tmp_path: Path):
    fpath = tmp_path / "test.txt"
    process = _run_command(f"touch {fpath}", shell=True)
    assert process.returncode == 0
    assert fpath.exists()


def test_run_command_dry_run(tmp_path: Path):
    fpath = tmp_path / "test.txt"
    command = _run_command(["touch", fpath], dry_run=True)
    assert command == f"touch {fpath}"
    assert not fpath.exists()


def test_run_command_check():
    with pytest.raises(subprocess.CalledProcessError):
        _run_command(["which", "probably_fake_command"], check=True)


@pytest.mark.no_xdist
def test_run_command_no_markup(caplog: pytest.LogCaptureFixture, tmp_path: Path):
    # text with closing tag
    text = "[/]"

    # this should not raise a rich markup error
    fpath_txt = tmp_path / "test.txt"
    fpath_txt.write_text(text)
    _run_command(["cat", fpath_txt])
    assert text in caplog.text


@pytest.mark.no_xdist
def test_run_command_quiet(caplog: pytest.LogCaptureFixture):
    message = "This should be printed"
    _run_command(["echo", message], quiet=True)
    assert LogPrefix.RUN not in caplog.text
    assert message in caplog.text
