"""Terminal User Interface (TUI) for Nipoppy."""

import click

from nipoppy.cli import cli

try:
    from trogon import tui
except ImportError:
    from rich.markup import escape

    from nipoppy.logger import get_logger

    logger = get_logger(__name__)
    logger.error(
        "GUI not installed. Install it with [magenta]"
        + escape('pip install "nipoppy[gui]"')
        + "[/]"
    )
    raise SystemExit(127)


@tui()
@click.group()
def gui_cli():
    """Nipoppy GUI CLI."""
    pass


# Duplicate all commands from the base CLI to the GUI CLI
for cmd_name, cmd in cli.commands.items():
    gui_cli.add_command(cmd, name=cmd_name)


def main():
    """Run the GUI CLI."""
    gui_cli(["tui"])
