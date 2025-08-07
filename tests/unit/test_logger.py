"""Tests for the logger module."""

import logging
from pathlib import Path

import pytest

import nipoppy.logger  # for monkeypatching
from nipoppy.logger import add_logfile, get_logger


@pytest.mark.parametrize("verbose", [False, True])
@pytest.mark.parametrize("name", ["my_logger", "workflow_logger"])
def test_get_logger(verbose: bool, name: str):
    logger = get_logger(verbose=verbose, name=name)
    assert isinstance(logger, logging.Logger)
    assert logger.name == name


@pytest.mark.parametrize("verbose", [False, True])
def test_get_logger_capsys(verbose: bool, capsys: pytest.CaptureFixture):
    logger = get_logger(verbose=verbose)
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


def test_get_logger_no_propagate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(nipoppy.logger, "IS_TESTING", False)
    logger = get_logger()
    assert not logger.propagate


def test_add_logfile(tmp_path: Path):
    logger = logging.getLogger("test_add_logfile")
    fpath_log = tmp_path / "test.log"
    add_logfile(logger, fpath_log)
    logger.info("Test")
    assert fpath_log.exists()


def test_add_logfile_mkdir(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    logger = logging.getLogger("test_add_logfile_mkdir")
    fpath_log = tmp_path / "log" / "test.log"
    add_logfile(logger, fpath_log)
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
