"""Tests for nipoppy.console module."""

import io

import pytest
from rich.logging import RichHandler
from rich.table import Table

from nipoppy.console import (
    _INDENT,
    CONSOLE_STDERR,
    CONSOLE_STDOUT,
    _Console,
)
from nipoppy.logger import get_logger


@pytest.fixture
def console():
    """Fixture for Console instance."""
    return _Console()


def test_global_consoles():
    assert CONSOLE_STDOUT.stderr is False
    assert CONSOLE_STDERR.stderr is True


def test_console_with_padding_confirm(console: _Console, capsys: pytest.CaptureFixture):
    # check that no newline is added at the end of the prompt
    message = "test message"
    console.confirm_with_indent(message, stream=io.StringIO("y\n"))
    captured = capsys.readouterr()
    assert captured.out.startswith(f"{' ' * _INDENT}{message}")
    assert not captured.out.endswith("\n")


def test_console_with_padding_print_table(
    console: _Console, capsys: pytest.CaptureFixture
):
    table = Table()
    table.add_column("Column 1")
    table.add_row("Row 1")
    console.print_with_indent(table)
    captured = capsys.readouterr()
    print(f"{captured.out=}")
    assert captured.out.startswith(" " * _INDENT)
    assert captured.out.endswith("\n")


def test_console_with_padding_loghandler_no_indent(capsys: pytest.CaptureFixture):
    logger = get_logger("test_logger")
    for handler in logger.handlers:
        if isinstance(handler, RichHandler):
            assert isinstance(handler.console, _Console)

    # check that no indent is added
    message = "test message"
    logger.info(message)
    captured = capsys.readouterr()
    assert not captured.out.startswith(" " * _INDENT)
    assert captured.out[_INDENT:].startswith(message)  # check alignment
