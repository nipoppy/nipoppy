"""Define a custom Click group that supports command aliases and preserves order."""

import sys
from contextlib import contextmanager

from pydantic_core import ValidationError

from nipoppy.env import BUG_REPORT_URL, DISCORD_URL
from nipoppy.exceptions import NipoppyError, ReturnCode
from nipoppy.logger import get_logger

logger = get_logger()


@contextmanager
def exception_handler(workflow):
    """Handle exceptions raised during workflow execution."""
    try:
        yield workflow
    except NipoppyError as e:
        workflow.return_code = e.code
        logger.error(e)
        hint = e.troubleshooting_hint
        if hint is not None:
            logger.info(f"Troubleshooting: {hint}")
    except ValidationError as e:
        workflow.return_code = ReturnCode.INVALID_CONFIG
        logger.error(e)
        logger.info(
            "Troubleshooting: Review your configuration fields and value types."
        )
    except SystemExit as e:
        workflow.return_code = e.code or ReturnCode.UNKNOWN_FAILURE
        logger.error(e)
    except Exception:
        workflow.return_code = ReturnCode.UNKNOWN_FAILURE
        logger.exception("Unexpected error occurred")
        logger.info(
            "This failure was unexpected. Please report it with the command you ran "
            f"and relevant logs on GitHub: {BUG_REPORT_URL} or ask on Discord: "
            f"{DISCORD_URL}"
        )
    finally:
        sys.exit(workflow.return_code)
