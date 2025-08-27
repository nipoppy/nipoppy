"""Logger."""

import logging
import types
from functools import partial
from pathlib import Path
from typing import Optional

import rich_click as click
from rich.logging import RichHandler

from nipoppy.console import _Console
from nipoppy.env import IS_TESTING, LogColor, StrOrPathLike

DATE_FORMAT = "[%Y-%m-%d %X]"
FORMAT_RICH = "%(message)s"
FORMAT_FILE = "%(asctime)s %(levelname)-7s %(message)s"


def success(self, message, *args, **kwargs):
    """Log a success message.

    Standardize format for success messages.

    Parameters
    ----------
    message : str
        The message to log.
    """
    self._log(
        logging.INFO,
        f"[{LogColor.SUCCESS}]{message} 🎉🎉🎉[/]",
        args,
        **kwargs,
    )


def get_logger(
    name: Optional[str] = "nipoppy", verbose: bool = False
) -> logging.Logger:
    """Create/get a logger with rich formatting."""
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.DEBUG)

    # propagate should be False to avoid duplicates from root logger
    # except when testing because otherwise pytest does not capture the logs
    if not IS_TESTING:
        logger.propagate = False

    # partially instantiate RichHandler
    rich_handler = partial(
        RichHandler,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_suppress=[click],
    )

    # stderr: ERROR and CRITICAL
    stderr_handler = rich_handler(logging.ERROR, console=_Console(stderr=True))
    logger.addHandler(stderr_handler)

    # stdout: INFO and WARNING
    # If verbosity is enabled, also display DEBUG
    verbosity = logging.DEBUG if verbose else logging.INFO
    stdout_handler = rich_handler(verbosity, console=_Console(stderr=False))
    stdout_handler.addFilter(lambda record: record.levelno <= logging.WARNING)
    logger.addHandler(stdout_handler)

    # Add custom method for SUCCESS level
    setattr(logger, "success", types.MethodType(success, logger))

    return logger


def add_logfile(logger: logging.Logger, fpath_log: StrOrPathLike) -> None:
    """Add a file handler to the logger."""
    fpath_log: Path = Path(fpath_log)

    dpath_log = fpath_log.parent
    if not dpath_log.exists():
        logger.warning(f"Creating log directory because it does not exist: {dpath_log}")
        dpath_log.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(fpath_log)
    file_handler.setFormatter(logging.Formatter(FORMAT_FILE, datefmt=DATE_FORMAT))
    logger.addHandler(file_handler)
    logger.info(f"Writing the log to {fpath_log}")
    return logger


def capture_warnings(logger: logging.Logger) -> logging.Logger:
    """
    Capture warnings and log them to the same places as a reference logger.

    Note that logging.captureWarnings(True) must be called before this function.

    Parameters
    ----------
    logger : logging.Logger
        The reference logger, whose handlers will be added the the warnings logger

    Returns
    -------
    logging.Logger
        The warning logger
    """
    warnings_logger = logging.getLogger("py.warnings")
    for handler in logger.handlers:
        if handler not in warnings_logger.handlers:
            warnings_logger.addHandler(handler)
    return warnings_logger
