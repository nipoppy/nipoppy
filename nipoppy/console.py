"""Rich console with padding to align output with logger output."""

from __future__ import annotations

from rich.console import Console, RenderableType
from rich.padding import Padding
from rich.prompt import Confirm
from rich.status import Status
from rich.style import StyleType

_INDENT = 9  # match Rich logger offset


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
            spinner="dots",  # do not allow other spinners
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
        return Confirm.ask(f"{' ' * _INDENT}{prompt}", console=self, **kwargs)

    def print_with_indent(self, renderable: RenderableType, **kwargs) -> None:
        """Print a table with indenting."""
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
