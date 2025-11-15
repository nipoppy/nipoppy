"""Tests for nipoppy.console module."""

import io
import time

import pytest
from rich.logging import RichHandler
from rich.table import Table

from nipoppy.console import _INDENT, CONSOLE_STDERR, CONSOLE_STDOUT, _Console, _Status


@pytest.fixture
def console():
    """Fixture for Console instance."""
    return _Console(force_terminal=True)


def test_global_consoles():
    assert CONSOLE_STDOUT.stderr is False
    assert CONSOLE_STDOUT.indent == _INDENT
    assert CONSOLE_STDERR.stderr is True
    assert CONSOLE_STDERR.indent == _INDENT


@pytest.mark.no_xdist
def test_console_confirm(console: _Console, capsys: pytest.CaptureFixture):
    # check that no newline is added at the end of the prompt
    message = "test message"
    # use a prompt that has multiple lines
    console.confirm(
        "\n".join([message] * 2), kwargs_call={"stream": io.StringIO("y\n")}
    )
    captured = capsys.readouterr()
    assert all(
        [
            line.startswith(f"{' ' * _INDENT}{message}")
            for line in captured.out.splitlines()
        ]
    )
    assert not captured.out.endswith("\n")


@pytest.mark.no_xdist
def test_console_print(console: _Console, capsys: pytest.CaptureFixture):
    table = Table()
    table.add_column("Column 1")
    table.add_row("Row 1")
    console.print(table, with_indent=True)
    captured = capsys.readouterr()
    assert captured.out.startswith(" " * _INDENT)
    assert captured.out.endswith("\n")


@pytest.mark.no_xdist
def test_console_no_indent_in_log(logger, capsys: pytest.CaptureFixture):
    for handler in logger.handlers:
        if isinstance(handler, RichHandler):
            assert isinstance(handler.console, _Console)

    # check that no indent is added
    message = "test message"
    logger.info(message)
    captured = capsys.readouterr()
    assert not captured.out.startswith(" " * _INDENT)
    assert captured.out[_INDENT:].startswith(message)  # check alignment


def test_console_status(console: _Console):
    assert isinstance(console.status(""), _Status)


@pytest.mark.no_xdist
def test_status_context_manager(console: _Console, capsys: pytest.CaptureFixture):
    message = "test status"
    with _Status(message, console=console):
        time.sleep(0.1)

    captured = capsys.readouterr()
    assert f"{' ' * (_INDENT - 2)}{message}" in captured.out


@pytest.mark.no_xdist
def test_status_update(console: _Console, capsys: pytest.CaptureFixture):
    message = "test update"
    with console.status("tmp") as status:
        time.sleep(0.1)
        status.update(message)

    captured = capsys.readouterr()
    assert f"{' ' * (_INDENT - 2)}{message}" in captured.out
