"""Custom Click groups."""

from collections.abc import Iterable
from pathlib import Path

import rich_click as click
from dotenv import load_dotenv

from nipoppy.cli.options import dataset_option
from nipoppy.env import DEFAULT_DOTENV_PATHS
from nipoppy.logger import get_logger
from nipoppy.utils.utils import is_nipoppy_project, process_template_str

logger = get_logger()


def _load_dotenv_files(
    dpath_root: Path, fpaths_dotenv: Iterable[str] = DEFAULT_DOTENV_PATHS
):
    """Load .env files."""
    dpath_root = is_nipoppy_project(dpath_root) or dpath_root

    for fpath_dotenv in fpaths_dotenv:
        fpath_dotenv = process_template_str(
            fpath_dotenv,
            dpath_root=dpath_root,
        )
        fpath_dotenv = Path(fpath_dotenv).expanduser()
        if fpath_dotenv.is_file():
            # the logger only logs at INFO or higher at this point
            logger.info(f"Loading environment variables from {fpath_dotenv}")

            # load_dotenv logs warnings instead of raising exceptions
            # so no need to catch them
            load_dotenv(fpath_dotenv, override=False)


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


class OrderedAliasedGroupWithDotenv(OrderedAliasedGroup):
    """OrderedAliasedGroup that also loads .env files before executing any command."""

    @click.command()
    @dataset_option
    def _dummy_cli(**params):
        """Define a dummy CLI for dataset path retrieval."""
        pass

    def make_context(self, info_name, args, *remaining_args, **kwargs):
        """Load .env files."""
        dummy_ctx = self._dummy_cli.make_context(
            "dataset_retriever",
            args[:],
            resilient_parsing=True,
        )
        dpath_root = dummy_ctx.params.get("dpath_root")

        _load_dotenv_files(dpath_root)

        return super().make_context(info_name, args, *remaining_args, **kwargs)
