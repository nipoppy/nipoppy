"""Tests for the logger module."""

import logging
from pathlib import Path

import pytest
import rich.logging

import nipoppy.logger  # for monkeypatching
from nipoppy.env import PROGRAM_NAME


@pytest.mark.parametrize("verbose", [False, True])
def test_get_logger(verbose: bool, logger, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(nipoppy.logger, "IS_TESTING", False)
    logger.verbose(verbose)
    assert logger.name == PROGRAM_NAME
    assert logger.level == logging.DEBUG

    assert isinstance(logger.handlers[0], rich.logging.RichHandler)
    assert logger.handlers[0].level == logging.ERROR

    assert isinstance(logger.handlers[1], rich.logging.RichHandler)
    if verbose:
        assert logger.handlers[1].level == logging.DEBUG
    else:
        assert logger.handlers[1].level == logging.INFO


@pytest.mark.no_xdist
@pytest.mark.parametrize("verbose", [False, True])
def test_get_logger_capsys(logger, verbose: bool, capsys: pytest.CaptureFixture):
    logger.verbose(verbose)
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


def test_add_file_handler(tmp_path: Path, logger, caplog: pytest.LogCaptureFixture):
    fpath_log = tmp_path / "log" / "test.log"
    logger.add_file_handler(fpath_log)
    logger.info("Test")
    assert fpath_log.exists()


def test_ignore_external_loggers(logger, caplog: pytest.LogCaptureFixture):
    external_logger = logging.getLogger("external_logger")
    external_logger.info("This is an external log message.")
    assert len(caplog.records) == 0

    logger.info("This is a nipoppy log message.")
    assert len(caplog.records) == 1
