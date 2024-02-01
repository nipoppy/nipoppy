"""Tests for the logger module."""
import logging
from pathlib import Path

import pytest

from nipoppy.logger import add_logfile, get_logger


@pytest.mark.parametrize("level", [logging.INFO, logging.DEBUG])
@pytest.mark.parametrize("name", ["my_logger", "workflow_logger"])
def test_get_logger(level: int, name: str):
    logger = get_logger(level=level, name=name)
    assert isinstance(logger, logging.Logger)
    assert logger.name == name


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
