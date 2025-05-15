"""Rich console with padding to align output with logger output."""

import types

from rich.console import Console, RenderableType
from rich.padding import Padding
from rich.prompt import Confirm
from rich.status import Status

_INDENT = 9  # match Rich logger offset


class _Console(Console):
    """Add utilities to indent output."""

    def confirm_with_indent(self, prompt: str, **kwargs) -> bool:
        """Prompt for confirmation with indenting."""
        return Confirm.ask(f"{' ' * _INDENT}{prompt}", console=self, **kwargs)

    def print_with_indent(self, renderable: RenderableType, **kwargs) -> None:
        """Print a table with indenting."""
        super().print(Padding.indent(renderable, _INDENT), **kwargs)

    def status_with_indent(self, status, speed=1.0, refresh_per_second=12.5) -> Status:
        """Override status to use padding."""

        def _padded_update(self: Status, status: RenderableType):
            return self.update(Padding.indent(status, _INDENT - 2))

        status = super().status(
            Padding.indent(status, _INDENT - 2),
            spinner="dots",
            spinner_style="status.spinner",
            speed=speed,
            refresh_per_second=refresh_per_second,
        )
        # add an update method to the status object that uses padding too
        setattr(status, "padded_update", types.MethodType(_padded_update, status))
        return status


CONSOLE_STDOUT = _Console(stderr=False)
CONSOLE_STDERR = _Console(stderr=True)
