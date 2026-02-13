"""Tests for CLI reference documentation completeness."""

from pathlib import Path

import pytest

from nipoppy.cli.cli import cli
from tests.conftest import list_commands


def get_doc_filename(command_name):
    """Convert command name to expected documentation filename."""
    # Replace spaces and hyphens with underscores and add .rst extension
    return command_name.replace(" ", "_").replace("-", "_") + ".rst"


@pytest.mark.parametrize("command", list_commands(cli))
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
        / "cli_reference"
        / doc_filename
    )

    # Check if the documentation file exists
    assert doc_path.exists(), (
        f"Missing CLI reference documentation for command '{command}'. "
        f"Expected file: {doc_path}. "
        f"Please create the documentation file following the pattern of other "
        f"CLI reference files in docs/source/cli_reference/."
    )
