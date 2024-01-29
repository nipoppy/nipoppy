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
def test_get_logger(level: int):
    """Test that the logger can be retrieved."""
    logger = get_logger(level=level)
    assert isinstance(logger, logging.Logger)
