"""Tests for the logger."""
import logging

import pytest

from nipoppy.logger import get_logger


@pytest.mark.parametrize(
    "level",
    [
        logging.INFO,
        logging.DEBUG,
    ],
)
@pytest.mark.parametrize(
    "name",
    [
        "my_logger",
        "workflow_logger",
    ],
)
def test_get_logger(level: int, name: str):
    """Test that the logger can be retrieved."""
    logger = get_logger(level=level, name=name)
    assert isinstance(logger, logging.Logger)
    assert logger.name == name
