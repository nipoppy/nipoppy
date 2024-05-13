"""Logger."""

import logging
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler

DATE_FORMAT = "[%Y-%m-%d %X]"
FORMAT_RICH = "%(message)s"
FORMAT_FILE = "%(asctime)s %(levelname)-7s %(message)s"


def get_logger(
    name: Optional[str] = "nipoppy", level: int = logging.INFO
) -> logging.Logger:
    """Create/get a logger with rich formatting."""
    # create logger
    logger = logging.getLogger(name=name)
    logger.setLevel(level)

    # stream to stderr with rich formatting
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(FORMAT_RICH, datefmt=DATE_FORMAT))
    logger.addHandler(stream_handler)
    logger.addHandler(RichHandler(show_time=False, markup=True, rich_tracebacks=True))
    return logger


def add_logfile(logger: logging.Logger, fpath_log: Path | str) -> None:
    """Add a file handler to the logger."""
    fpath_log = Path(fpath_log)

    dpath_log = fpath_log.parent
    if not dpath_log.exists():
        logger.warning(f"Creating log directory because it does not exist: {dpath_log}")
        dpath_log.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(fpath_log)
    file_handler.setFormatter(logging.Formatter(FORMAT_FILE, datefmt=DATE_FORMAT))
    logger.addHandler(file_handler)
    logger.info(f"Writing the log to {fpath_log}")
    return logger
