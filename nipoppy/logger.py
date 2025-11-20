"""Logger."""

import logging
from functools import partial
from pathlib import Path
from typing import Optional

import rich_click as click
from rich.logging import RichHandler
from typing_extensions import Self

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
    WARNING = "yellow"
    FAILURE = "red"


class NipoppyLogger(logging.Logger):
    """Custom logger for Nipoppy."""

    NAME: str = "nipoppy"

    def __init__(self, *args, **kwargs):
        """Initialize the Nipoppy logger."""
        super().__init__(*args, **kwargs)
        self._stdout_handler: Optional[RichHandler] = None
        self._file_handler: Optional[logging.FileHandler] = None

        self.setLevel(logging.DEBUG)  # File logging: DEBUG and above
        # stderr: ERROR and CRITICAL
        self.stderr_handler = rich_handler(logging.ERROR, console=CONSOLE_STDERR)
        self.addHandler(self.stderr_handler)

    def _cleanup_handlers(self, handler: Optional[logging.Handler] = None) -> None:
        """Close and remove a handler from the logger.

        Parameters
        ----------
        handler : logging.Handler
            The handler to remove.
        """
        if handler:
            handler.close()
            self.removeHandler(handler)

    def set_verbose(self, verbose: bool) -> Self:
        """Set the verbose of the logger.

        Parameters
        ----------
        verbose : bool
            If True, set verbose to DEBUG, else to INFO.

        Returns
        -------
        Self
            The nipoppy logger
        """
        # Remove existing stdout handler with previous verbosity level
        self._cleanup_handlers(self._stdout_handler)

        # stdout: INFO and WARNING
        # If verbose is enabled, also display DEBUG
        log_level = logging.DEBUG if verbose else logging.INFO
        self._stdout_handler = rich_handler(log_level, console=CONSOLE_STDOUT)
        self._stdout_handler.addFilter(lambda record: record.levelno <= logging.WARNING)
        self.addHandler(self._stdout_handler)
        return self

    def add_file_handler(self, file: Path) -> Self:
        """Add a file handler to the logger.

        Parameters
        ----------
        file : Path
            The file path to write the log to.

        Returns
        -------
        Self
            The nipoppy logger
        """
        # Only one file handler allowed
        self._cleanup_handlers(self._file_handler)

        file.parent.mkdir(parents=True, exist_ok=True)
        self._file_handler = logging.FileHandler(file)
        self._file_handler.setFormatter(
            logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT)
        )
        self.addHandler(self._file_handler)
        self.info(f"Writing the log to {file}")
        return self

    def set_capture_warnings(self, capture: bool = True) -> Self:
        """Configure whether warnings are captured.

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

    def success(self, message, args=None, **kwargs) -> None:
        """Log a success message.

        Standardize format for success messages.

        Parameters
        ----------
        message : str
            The message to log.
        """
        self.info(f"[{LogColor.SUCCESS}]{message} 🎉🎉🎉[/]")

    def failure(self, message, args=None, **kwargs) -> None:
        """Log a failure message.

        Standardize format for failure messages.

        Parameters
        ----------
        message : str
            The message to log.
        """
        self.error(f"[{LogColor.FAILURE}]{message} ❌❌❌[/]")

    def warning(self, message, args=None, **kwargs) -> None:
        """Log a warning message.

        Standardize format for warning messages.

        Parameters
        ----------
        message : str
            The message to log.
        """
        super().warning(f"[{LogColor.WARNING}]{message} ⚠️⚠️⚠️[/]")


def get_logger(verbose: bool = False) -> NipoppyLogger:
    """Retrieve the logger."""
    logging.setLoggerClass(NipoppyLogger)
    logger = logging.getLogger(NipoppyLogger.NAME)
    logger.set_verbose(verbose)

    # Reset to default logger class
    # Otherwise, external libraries will also use NipoppyLogger
    # This can lead to error when enabling rich's markup.
    logging.setLoggerClass(logging.Logger)

    return logger
