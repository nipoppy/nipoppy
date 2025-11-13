"""Logger."""

import logging
from functools import partial
from pathlib import Path
from typing import Self

import rich_click as click
from rich.logging import RichHandler

from nipoppy.console import CONSOLE_STDERR, CONSOLE_STDOUT
from nipoppy.env import IS_TESTING

DATE_FORMAT = "[%Y-%m-%d %X]"
CONSOLE_FORMAT = "%(message)s"
FILE_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"

rich_handler = partial(
    RichHandler,
    show_time=False,
    show_path=False,
    markup=True,
    rich_tracebacks=True,
    tracebacks_suppress=[click],
)


class LogColor:
    """Colors for logging."""

    SUCCESS = "green"
    PARTIAL_SUCCESS = "yellow"
    FAILURE = "red"


class NipoppyLogger(logging.Logger):
    """Custom logger for Nipoppy."""

    name: str = "nipoppy"

    def __init__(
        self,
    ):
        """Initialize the Nipoppy logger."""
        super().__init__(self.name)

        # propagate should be False to avoid duplicates from root logger
        # except when testing because otherwise pytest does not capture the logs
        if not IS_TESTING:
            self.propagate = False

        # stderr: ERROR and CRITICAL
        stderr_handler = rich_handler(logging.ERROR, console=CONSOLE_STDERR)
        self.addHandler(stderr_handler)

    def verbose(self, verbosity: bool) -> Self:
        """Set the verbosity of the logger.

        Parameters
        ----------
        verbose : bool
            If True, set verbosity to DEBUG, else to INFO.

        Returns
        -------
        Self
            The nipoppy logger
        """
        # stdout: INFO and WARNING
        # If verbosity is enabled, also display DEBUG
        verbosity = logging.DEBUG if verbosity else logging.INFO
        stdout_handler = rich_handler(verbosity, console=CONSOLE_STDOUT)
        stdout_handler.addFilter(lambda record: record.levelno <= logging.WARNING)
        self.addHandler(stdout_handler)
        return self

    def add_file_handler(self, file: Path) -> logging.Handler:
        """Add a file handler to the logger."""
        file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(file)
        handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT))
        self.addHandler(handler)
        self.info(f"Writing the log to {file}")
        return handler

    def capture_warnings(self, capture: bool = True) -> Self:
        """
        Capture warnings and log them to the same places as a reference logger.

        Parameters
        ----------
        capture : bool, optional
            Whether to capture warnings, by default True

        Returns
        -------
        Self
            The nipoppy logger
        """
        if capture:
            logging.captureWarnings(True)
            warnings_logger = logging.getLogger("py.warnings")
            for handler in _logger.handlers:
                if handler not in warnings_logger.handlers:
                    warnings_logger.addHandler(handler)
        else:
            logging.captureWarnings(False)

        return self


_logger = NipoppyLogger()
_logger.setLevel(logging.DEBUG)


def get_logger() -> NipoppyLogger:
    """Retrieve the logger."""
    return _logger


###########
# Plugins #
###########
def plugin(func):
    """Decorate a function to add it as a method to NipoppyLogger."""
    setattr(NipoppyLogger, func.__name__, func)
    return func


@plugin
def success(self, message, args=None, **kwargs):
    """Log a success message.

    Standardize format for success messages.

    Parameters
    ----------
    message : str
        The message to log.
    """
    self._log(
        level=logging.INFO,
        msg=f"[{LogColor.SUCCESS}]{message} 🎉🎉🎉[/]",
        args=args,
        **kwargs,
    )
