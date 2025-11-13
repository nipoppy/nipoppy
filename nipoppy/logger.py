"""Logger."""

import logging
from functools import partial
from pathlib import Path
from typing import Self

import rich_click as click
from rich.logging import RichHandler

from nipoppy.console import CONSOLE_STDERR, CONSOLE_STDOUT

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

    NAME: str = "nipoppy"

    def __init__(self, *args, **kwargs):
        """Initialize the Nipoppy logger."""
        super().__init__(*args, **kwargs)
        # self.propagate = False
        print(self.name)
        self.setLevel(logging.DEBUG)
        self._reset_config()

    def _reset_config(self):
        """Reset the logger configuration."""
        self._configure_console()
        self.verbose(False)

    def _configure_console(self):
        """Configure console logging."""
        if hasattr(self, "stderr_handler"):
            self.stderr_handler.close()
            self.removeHandler(self.stderr_handler)
        # stderr: ERROR and CRITICAL
        self.stderr_handler = rich_handler(logging.ERROR, console=CONSOLE_STDERR)
        self.addHandler(self.stderr_handler)

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
        if hasattr(self, "stdout_handler"):
            self.stdout_handler.close()
            self.removeHandler(self.stdout_handler)
        # stdout: INFO and WARNING
        # If verbosity is enabled, also display DEBUG
        log_level = logging.DEBUG if verbosity else logging.INFO
        self.stdout_handler = rich_handler(log_level, console=CONSOLE_STDOUT)
        self.stdout_handler.addFilter(lambda record: record.levelno <= logging.WARNING)
        self.addHandler(self.stdout_handler)
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
            for handler in self.handlers:
                if handler not in warnings_logger.handlers:
                    warnings_logger.addHandler(handler)
        else:
            logging.captureWarnings(False)

        return self

    def success(self, message, args=None, **kwargs):
        """Log a success message.

        Standardize format for success messages.

        Parameters
        ----------
        message : str
            The message to log.
        """
        self.info(f"[{LogColor.SUCCESS}]{message} 🎉🎉🎉[/]")


logging.basicConfig()


def get_logger() -> NipoppyLogger:
    """Retrieve the logger."""
    logging.setLoggerClass(NipoppyLogger)
    logger = logging.getLogger(NipoppyLogger.NAME)

    # Reset to default logger class
    # Otherwise, external libraries will also use NipoppyLogger
    # This can lead to error when enabling rich's markup.
    logging.setLoggerClass(logging.Logger)

    return logger
