"""Tests for the logger module."""

import logging
from pathlib import Path

import pytest

import nipoppy.logger  # for monkeypatching
from nipoppy.env import PROGRAM_NAME
from nipoppy.logger import get_logger


@pytest.mark.parametrize("verbose", [False, True])
def test_get_logger(verbose: bool, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(nipoppy.logger, "IS_TESTING", False)
    logger = get_logger()
    logger.verbose(verbose)
    assert logger.level == (logging.DEBUG if verbose else logging.INFO)
    assert logger.name == PROGRAM_NAME


@pytest.mark.parametrize("verbose", [False, True])
def test_get_logger_capsys(verbose: bool, capsys: pytest.CaptureFixture):
    logger = get_logger()
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


def test_get_logger_level():
    # non-root loggers have level set to NOTSET and inherit from "parent" loggers
    # so we need to check the root logger to see if the level was set correctly
    logger = get_logger()
    assert logger.level == logging.DEBUG


def test_add_file_handler(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    logger = get_logger()
    fpath_log = tmp_path / "log" / "test.log"
    logger.add_file_handler(fpath_log)
    logger.info("Test")
    assert "Creating log directory" in caplog.text
    assert fpath_log.exists()


def test_no_extra_logs(caplog: pytest.LogCaptureFixture):
    caplog.clear()

    logger = get_logger()
    logger.propagate = True

    # doing this should not log anything
    import nipoppy.workflows  # noqa F401

    logger.info("TEST")
    assert len(caplog.records) == 1
