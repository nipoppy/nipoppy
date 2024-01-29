"""Logger."""
import logging

from rich.logging import RichHandler


def get_logger(level: int = logging.INFO) -> logging.Logger:
    """Create/get a logger with rich formatting."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%Y-%m-%d %X]",
        handlers=[RichHandler()],
    )
    return logging.getLogger()
