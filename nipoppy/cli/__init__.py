"""Define a custom Click group that supports command aliases and preserves order."""

import sys
from contextlib import contextmanager

import rich_click as click
from pydantic_core import ValidationError

from nipoppy.env import PROGRAM_NAME, ReturnCode
from nipoppy.exceptions import NipoppyError
from nipoppy.logger import get_logger


# TODO once logger is extracted from the workflows, we could remove the `workflow`
# parameter and use as a standalone context manager
@contextmanager
def exception_handler(workflow):
    """Handle exceptions raised during workflow execution."""
    try:
        yield workflow
    except NipoppyError as e:
        workflow.return_code = e.code
        workflow.logger.error(e)
    except ValidationError as e:
        workflow.return_code = ReturnCode.INVALID_CONFIG
        workflow.logger.error(e)
    except SystemExit as e:
        workflow.return_code = e.code or ReturnCode.UNKNOWN_FAILURE
        workflow.logger.error(e)
    except Exception:
        workflow.return_code = ReturnCode.UNKNOWN_FAILURE
        workflow.logger.exception("Unexpected error occurred")
    finally:
        sys.exit(workflow.return_code)


logger = get_logger(
    name=f"{PROGRAM_NAME}.{__name__}",
)


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
