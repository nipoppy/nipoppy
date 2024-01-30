"""Logger."""
import logging
from typing import Optional

from rich.logging import RichHandler


def get_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Create/get a logger with rich formatting."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%Y-%m-%d %X]",
        handlers=[RichHandler()],
    )
    return logging.getLogger(name=name)
