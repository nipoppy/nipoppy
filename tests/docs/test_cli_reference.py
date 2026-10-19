"""Tests for CLI reference documentation completeness."""

from pathlib import Path

import pytest
import rich_click as click

from nipoppy.cli.cli import cli
from tests.conftest import list_cli_commands


def get_doc_filename(command_name):
    """Convert command name to expected documentation filename."""
    # Replace spaces and hyphens with underscores and add .rst extension
    return command_name.replace(" ", "_").replace("-", "_") + ".rst"


@pytest.mark.parametrize("command", list_cli_commands(cli, include_hidden=False))
def test_cli_command_has_documentation(command: str):
    """Test that each CLI command has a corresponding documentation page.

    This ensures that the CLI reference documentation is complete and up-to-date.
    """
    # Get the expected documentation file path
    doc_filename = get_doc_filename(command)
    doc_path = (
        Path(__file__).parents[2]  # Path to repo root
        / "docs"
        / "source"
        / "reference/cli_reference"
        / doc_filename
    )

    # Check if the documentation file exists
    assert doc_path.exists(), (
        f"Missing CLI reference documentation for command '{command}'. "
        f"Expected file: {doc_path}. "
        f"Please create the documentation file following the pattern of other "
        f"CLI reference files in docs/source/reference/cli_reference/."
    )


@pytest.mark.parametrize(
    "command_name",
    list_cli_commands(cli, include_hidden=False, include_group=False),
)
def test_cli_all_options_grouped(command_name: str):
    """Test that all non-hidden CLI options are assigned to an option group."""
    grouped_options = {
        opt
        for group in click.rich_click.OPTION_GROUPS["nipoppy *"]
        for opt in group["options"]
    }

    # get Click Command object
    command = cli
    for command_component in command_name.split(" "):
        command = command.get_command(None, command_component)

    for param in command.params:
        if isinstance(param, click.Option) and not param.hidden:
            assert any(opt in grouped_options for opt in param.opts), (
                f"Option {param.opts} of '{command_name}' is not in any option group."
            )
