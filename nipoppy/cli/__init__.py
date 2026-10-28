"""Define a custom Click group that supports command aliases and preserves order."""

import sys
from contextlib import contextmanager


@contextmanager
def exception_handler(workflow):
    """Exit with the workflow return code."""
    try:
        yield workflow
    finally:
        sys.exit(workflow.return_code)
