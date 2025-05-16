"""Rich console with padding to align output with logger output."""

from __future__ import annotations

from rich.console import Console, RenderableType, RenderResult
from rich.padding import Padding
from rich.prompt import Confirm
from rich.status import Status
from rich.style import StyleType

_INDENT = 9  # match Rich logger offset


class _PaddingWithoutNewline(Padding):
    """
    Padding that does not add a newline or spaces at the end.

    Used to add indentation to the prompt in _Confirm without adding a newline.
    """

    def __rich_console__(self, *args, **kwargs) -> RenderResult:
        """Return a list of rich.segment.Segment objects to be printed."""
        segments = list(super().__rich_console__(*args, **kwargs))

        # remove trailing spaces and newlines
        while len(segments) > 0 and segments[-1].text.strip() == "":
            segments.pop()
        return segments


class _Confirm(Confirm):
    def make_prompt(self, *args) -> RenderableType:
        """Override to add indenting."""
        return _PaddingWithoutNewline(super().make_prompt(*args), (0, 0, 0, _INDENT))


class _Status(Status):
    """Add utilities to indent output."""

    def __init__(
        self,
        status: RenderableType,
        *,
        console: Console | None = None,
        spinner_style: StyleType = "status.spinner",
        speed: float = 1,
        refresh_per_second: float = 12.5,
    ):
        super().__init__(
            status=Padding.indent(status, _INDENT - 2),
            console=console,
            spinner="dots",  # do not allow other spinners since the indent is fixed
            spinner_style=spinner_style,
            speed=speed,
            refresh_per_second=refresh_per_second,
        )

    def update(self, status: RenderableType) -> None:
        """Update the status with indenting."""
        super().update(Padding.indent(status, _INDENT - 2))


class _Console(Console):
    """Add utilities to indent output."""

    def confirm_with_indent(self, prompt: str, **kwargs) -> bool:
        """Prompt for confirmation with indenting."""
        return _Confirm.ask(prompt, console=self, **kwargs)

    def print_with_indent(self, renderable: RenderableType, **kwargs) -> None:
        """Print an object with indenting."""
        super().print(Padding.indent(renderable, _INDENT), **kwargs)

    def status_with_indent(self, status, **kwargs) -> _Status:
        """Override status to use padding."""
        return _Status(
            status=status,
            console=self,
            **kwargs,
        )


CONSOLE_STDOUT = _Console(stderr=False)
CONSOLE_STDERR = _Console(stderr=True)
