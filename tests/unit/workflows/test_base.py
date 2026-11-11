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


class MyCustomException(NipoppyError):
    code = 999


class TestRun:
    def test_run(self, workflow: BaseWorkflow):
        """Test that run() completes without error."""
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
        self,
        workflow: BaseWorkflow,
        mocker: pytest_mock.MockerFixture,
        return_code,
        expected_return_code,
    ):
        """Test that run() handles SystemExit correctly.

        SystemExit should set the workflow return code to the
        exception's code. Other exceptions should set it to UNKNOWN_FAILURE.
        """

        def run_main():
            if return_code is None:
                raise SystemExit
            else:
                raise SystemExit(return_code)

        mocker.patch.object(workflow, "run_main", side_effect=run_main)
        with pytest.raises(SystemExit):
            workflow.run()

        assert workflow.return_code == expected_return_code

    @pytest.mark.parametrize(
        "exception,return_code",
        [
            (NipoppyError, NipoppyError.code),
            (ZenodoAPIError, ReturnCode.KNOWN_FAILURE),
            (MyCustomException, MyCustomException.code),
        ],
    )
    def test_handle_exception_nipoppy_exception(
        self,
        workflow: BaseWorkflow,
        mocker: pytest_mock.MockerFixture,
        exception: Exception,
        return_code: int,
    ):
        """Test that run() handles exceptions correctly.

        NipoppyError and its subclasses should set the workflow return code to the
        exception's code. Other exceptions should set it to UNKNOWN_FAILURE.
        """
        mocker.patch.object(workflow, "run_main", side_effect=exception)
        with pytest.raises(exception):
            workflow.run()

        assert workflow.return_code == return_code

    @pytest.mark.parametrize("hint", ["", "This is a hint."])
    def test_handle_exception_nipoppy_exception_logs_custom_hint(
        self,
        hint,
        workflow: BaseWorkflow,
        mocker: pytest_mock.MockerFixture,
        caplog: pytest.LogCaptureFixture,
    ):
        """Known NipoppyError should emit custom hint when provided."""
        mocker.patch.object(
            workflow,
            "run_main",
            side_effect=NipoppyError("Invalid project config", hint=hint),
        )
        with pytest.raises(NipoppyError):
            workflow.run()

        assert any(
            "Troubleshooting:" in record.message and hint in record.message
            for record in caplog.records
        )

    def test_handle_exception_nipoppy_exception_logs_default_hint(
        self,
        workflow: BaseWorkflow,
        mocker: pytest_mock.MockerFixture,
        caplog: pytest.LogCaptureFixture,
    ):
        """Known NipoppyError should emit default hint when none provided."""
        default_hint = "This is a default hint."
        e = NipoppyError("Invalid project config", hint=None)
        e.default_hint = default_hint
        mocker.patch.object(workflow, "run_main", side_effect=e)
        with pytest.raises(NipoppyError):
            workflow.run()

        assert any(
            f"Troubleshooting: {default_hint}" in record.message
            for record in caplog.records
        )

    def test_handle_exception_json_error(
        self,
        workflow: BaseWorkflow,
        mocker: pytest_mock.MockerFixture,
        caplog: pytest.LogCaptureFixture,
    ):
        """Test that JSONError includes the file path in the error message."""
        fpath = "invalid.json"
        mocker.patch.object(
            workflow,
            "run_main",
            side_effect=JSONError(
                json.JSONDecodeError("Invalid JSON", "{}", 10),
                fpath=Path(fpath),
            ),
        )
        with pytest.raises(JSONError):
            workflow.run()
        assert any(
            f"Invalid JSON: {fpath}: line 1 column 11 (char 10)" in record.message
            for record in caplog.records
        )

    @pytest.mark.parametrize(
        "return_code",
        [(None), (ReturnCode.UNKNOWN_FAILURE), (ReturnCode.INVALID_ARGUMENT)],
    )
    @pytest.mark.parametrize("exception", [Exception, RuntimeError])
    def test_handle_exception_unknown_exception(
        self,
        workflow: BaseWorkflow,
        mocker: pytest_mock.MockerFixture,
        exception,
        return_code,
        caplog: pytest.LogCaptureFixture,
    ):
        """Test that run() handles exceptions correctly.

        Unknown exception (Exception) should always set the return code to UNKNOWN_FAILURE.
        """

        def run_main():
            if return_code is None:
                raise exception
            else:
                raise exception(code=return_code)

        mocker.patch.object(workflow, "run_main", side_effect=run_main)
        with pytest.raises(Exception):
            workflow.run()

        # Exit code is always set to UNKNOWN_FAILURE for unknown exceptions
        assert workflow.return_code == ReturnCode.UNKNOWN_FAILURE
        assert any(BUG_REPORT_URL in record.message for record in caplog.records)
        assert any(DISCORD_URL in record.message for record in caplog.records)

    def test_handle_exception_pydantic_failed_validation(
        self,
        workflow: BaseWorkflow,
        mocker: pytest_mock.MockerFixture,
        caplog: pytest.LogCaptureFixture,
    ):
        """Test that run() handles pydantic ValidationError correctly."""
        from pydantic import BaseModel, ValidationError

        class MockedModel(BaseModel):
            field: int

        def run_main():
            MockedModel(field="invalid")  # will raise ValidationError

        mocker.patch.object(workflow, "run_main", side_effect=run_main)
        with pytest.raises(ValidationError):
            workflow.run()

        assert workflow.return_code == ReturnCode.INVALID_CONFIG
        assert any(
            "Troubleshooting:" in record.message
            and "Review your configuration fields and value types" in record.message
            for record in caplog.records
        )

    @pytest.mark.parametrize("method", ["run_setup", "run_main", "run_cleanup"])
    def test_run_exception(
        self, workflow: BaseWorkflow, method: str, mocker: pytest_mock.MockerFixture
    ):
        """Test that an exception raised during the workflow sets the return code."""
        mocker.patch.object(workflow, method, side_effect=MyCustomException)

        with pytest.raises(MyCustomException):
            workflow.run()

        assert workflow.return_code == MyCustomException.code


class TestRunAndExit:
    def test_run_and_exit_no_exception(self, workflow: BaseWorkflow):
        """run_and_exit() exits with SUCCESS when no exception occurs."""
        with pytest.raises(SystemExit) as exc_info:
            workflow.run_and_exit()

        assert exc_info.value.code == ReturnCode.SUCCESS

    def test_run_and_exit_exception(
        self, workflow: BaseWorkflow, mocker: pytest_mock.MockerFixture
    ):
        """run_and_exit() exits with the workflow return code on error."""
        mocker.patch.object(workflow, "run_main", side_effect=RuntimeError)

        with pytest.raises(SystemExit) as exc_info:
            workflow.run_and_exit()

        assert exc_info.value.code == ReturnCode.UNKNOWN_FAILURE


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
