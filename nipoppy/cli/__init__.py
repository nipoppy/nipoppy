"""Define a custom Click group that supports command aliases and preserves order."""

import sys
from contextlib import contextmanager

import rich_click as click

from nipoppy.env import PROGRAM_NAME, ReturnCode
from nipoppy.logger import get_logger


@contextmanager
def exception_handler(workflow):
    """Handle exceptions raised during workflow execution."""
    try:
        yield workflow
    except SystemExit:
        workflow.return_code = ReturnCode.UNKNOWN_FAILURE
    except Exception:
        workflow.logger.exception("Error while running nipoppy")
        if workflow.return_code == ReturnCode.SUCCESS:
            workflow.return_code = ReturnCode.UNKNOWN_FAILURE
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
