"""Define a custom Click group that supports command aliases and preserves order."""

import sys
from contextlib import contextmanager

import rich_click as click
from pydantic_core import ValidationError

from nipoppy.exceptions import NipoppyError, ReturnCode
from nipoppy.logger import get_logger

logger = get_logger()

BUG_REPORT_URL = (
    "https://github.com/nipoppy/nipoppy/issues/new/choose?template=bug_report.yml"
)
DISCORD_URL = "https://discord.gg/2VMKFRpjkm"


def _log_known_error(exception: NipoppyError) -> None:
    """Log known Nipoppy errors with actionable guidance."""
    logger.error(exception)
    hint = exception.troubleshooting_hint
    if hint:
        logger.warning(f"Suggested fix: {hint}")


def _log_validation_error(exception: ValidationError) -> None:
    """Log pydantic validation errors with actionable guidance."""
    logger.error(exception)
    logger.warning(
        "Suggested fix: Review your configuration fields and value types, then "
        "rerun once all validation errors are resolved."
    )


def _log_unexpected_error() -> None:
    """Log unexpected errors and direct users to support channels."""
    logger.exception("Unexpected error occurred")
    logger.warning(
        "This failure was unexpected. Please report it with the command you ran "
        f"and relevant logs on GitHub: {BUG_REPORT_URL} or ask on Discord: "
        f"{DISCORD_URL}"
    )


# TODO once logger is extracted from the workflows, we could remove the `workflow`
# parameter and use as a standalone context manager
@contextmanager
def exception_handler(workflow):
    """Handle exceptions raised during workflow execution."""
    try:
        yield workflow
    except NipoppyError as e:
        workflow.return_code = e.code
        _log_known_error(e)
    except ValidationError as e:
        workflow.return_code = ReturnCode.INVALID_CONFIG
        _log_validation_error(e)
    except SystemExit as e:
        workflow.return_code = e.code or ReturnCode.UNKNOWN_FAILURE
        logger.error(e)
    except Exception:
        workflow.return_code = ReturnCode.UNKNOWN_FAILURE
        _log_unexpected_error()
    finally:
        sys.exit(workflow.return_code)


class OrderedAliasedGroup(click.RichGroup):
    """Group that lists commands in the order they were added and supports aliases."""

    alias_map = {
        "doughnut": "track-curation",
        "run": "process",
        "track": "track-processing",
    }

    def list_commands(self, ctx):
        """List commands in the order they were added."""
        return list(self.commands.keys())

    def get_command(self, ctx, cmd_name):
        """Handle aliases.

        Given a context and a command name, this returns a Command object if it exists
        or returns None.
        """
        # recognized command
        command = click.Group.get_command(self, ctx, cmd_name)
        if command is not None:
            return command

        # aliases (to be deprecated)
        try:
            new_cmd_name = self.alias_map[cmd_name]
        except KeyError:
            return None

        logger.warning(
            (
                f"The '{cmd_name}' subcommand is deprecated and will cause an error "
                f"in a future version. Use '{new_cmd_name}' instead."
            ),
        )
        return click.Group.get_command(self, ctx, new_cmd_name)
