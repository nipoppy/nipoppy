"""Tests for the logger module."""

import logging
from pathlib import Path

import pytest
import rich.logging

from nipoppy.env import PROGRAM_NAME
from nipoppy.logger import LogColor, emphasize


def test_color():
    assert LogColor.SUCCESS == "green"
    assert LogColor.PARTIAL_SUCCESS == "yellow"
    assert LogColor.FAILURE == "red"


@pytest.mark.no_xdist
@pytest.mark.parametrize(
    "verbose, expected_level", [(False, logging.INFO), (True, logging.DEBUG)]
)
def test_get_logger(verbose: bool, expected_level: int, logger):
    logger.set_verbose(verbose)
    assert logger.name == PROGRAM_NAME
    assert logger.level == logging.DEBUG

    # stderr handler
    assert isinstance(logger.handlers[0], rich.logging.RichHandler)
    assert logger.handlers[0].level == logging.ERROR

    # stdout handler
    assert isinstance(logger.handlers[1], rich.logging.RichHandler)
    assert logger.handlers[1].level == expected_level


@pytest.mark.parametrize("verbose", [False, True])
@pytest.mark.no_xdist
def test_get_logger_capsys(logger, verbose: bool, capsys: pytest.CaptureFixture):
    logger.set_verbose(verbose)
    logger.debug("debug")
    logger.info("info")
    logger.warning("warning")
    logger.error("error")
    logger.critical("critical")
    captured = capsys.readouterr()

    # stdout
    if verbose:
        assert "debug" in captured.out
    else:
        assert "debug" not in captured.out
    assert "info" in captured.out
    assert "warning" in captured.out
    assert "error" not in captured.out
    assert "critical" not in captured.out

    # stderr
    assert "debug" not in captured.err
    assert "info" not in captured.err
    assert "warning" not in captured.err
    assert "error" in captured.err
    assert "critical" in captured.err


@pytest.mark.no_xdist
def test_add_file_handler(tmp_path: Path, logger):
    fpath_log = tmp_path / "log" / "test.log"
    logger.add_file_handler(fpath_log)
    logger.info("Test")
    assert fpath_log.exists()


@pytest.mark.no_xdist
def test_ignore_external_loggers(logger, caplog: pytest.LogCaptureFixture):
    external_logger = logging.getLogger("external_logger")
    external_logger.info("This is an external log message.")
    assert len(caplog.records) == 0

    logger.info("This is a nipoppy log message.")
    assert len(caplog.records) == 1


@pytest.mark.no_xdist
def test_warning_capture(
    caplog: pytest.LogCaptureFixture, recwarn: pytest.WarningsRecorder
):
    import warnings

    # Disable, then re-enable warning capture to ensure a clean state for the test
    # There's a conflict with pytest's own warning capture mechanism
    logging.captureWarnings(False)
    logging.captureWarnings(True)

    warning_msg = "This is a test warning."
    warnings.warn(warning_msg)

    # Warnings should not appear in 'recwarn' due to redirection
    assert len(recwarn) == 0

    # Check that the warning was captured in the logs
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert caplog.records[0].name == "py.warnings"  # Verify it came from the redirect


@pytest.mark.no_xdist
def test_success_markup(logger, caplog: pytest.LogCaptureFixture):
    # log a success message then check that it contains the success markup
    msg = "Operation completed successfully."
    logger.success(msg)
    assert caplog.records[0].message == f"[green]{msg} 🎉🎉🎉[/]"
    assert caplog.records[0].levelno == logging.INFO


@pytest.mark.no_xdist
def test_failure_markup(logger, caplog: pytest.LogCaptureFixture):
    # log a failure message then check that it contains the failure markup
    msg = "Operation failed."
    logger.failure(msg)
    assert caplog.records[0].message == f"[red]{msg}[/]"
    assert caplog.records[0].levelno == logging.ERROR


@pytest.mark.no_xdist
def test_warning_markup(logger, caplog: pytest.LogCaptureFixture):
    # log a warning message then check that it contains the warning markup
    msg = "This is a warning."
    logger.warning(msg)
    assert caplog.records[0].message == f"[yellow]{msg}[/]"
    assert caplog.records[0].levelno == logging.WARNING


def test_emphasize():
    msg = "message to emphasize"
    emphasized_msg = emphasize(msg)
    assert emphasized_msg == f"[bold magenta]{msg}[/]"
