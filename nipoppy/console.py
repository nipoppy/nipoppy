"""Rich console with padding to align output with logger output."""

from __future__ import annotations

import inspect
from functools import wraps
from pathlib import Path
from typing import Iterable, List, Optional

from rich.console import Console, RenderableType, RenderResult
from rich.padding import Padding
from rich.prompt import Confirm
from rich.status import Status
from rich.style import StyleType
from rich.text import TextType

_INDENT = 9  # match Rich logger offset

_DPATH_PACKAGE_ROOT = Path(__file__).parent.resolve()


def _force_indent_if_internal(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        """Set with_indent to True if the caller is from this package."""
        stack = inspect.stack()
        if len(stack) > 1:
            # the first frame is this function (wrapper), the second frame is the caller
            fpath_caller = Path(stack[1].filename).resolve()
            if fpath_caller.is_relative_to(_DPATH_PACKAGE_ROOT):
                kwargs["with_indent"] = True

        func(*args, **kwargs)

    return wrapper


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
    def __init__(
        self,
        prompt: TextType = "",
        indent: int = _INDENT,
        console: Console | None = None,
        password: bool = False,
        choices: List[str] | None = None,
        show_default: bool = True,
        show_choices: bool = True,
    ):
        super().__init__(
            prompt=prompt,
            console=console,
            password=password,
            choices=choices,
            show_default=show_default,
            show_choices=show_choices,
        )
        self.indent = indent

    def make_prompt(self, *args) -> RenderableType:
        """Override to add indenting."""
        return _PaddingWithoutNewline(
            super().make_prompt(*args), (0, 0, 0, self.indent)
        )


class _Status(Status):
    """Add utilities to indent output."""

    def __init__(
        self,
        status: RenderableType,
        console: Console | None = None,
        spinner_style: StyleType = "status.spinner",
        speed: float = 1,
        refresh_per_second: float = 12.5,
        indent: int = _INDENT,
    ):
        self.indent = indent
        super().__init__(
            status=Padding.indent(status, self.indent - 2),
            console=console,
            spinner="dots",  # do not allow other spinners since the indent is fixed
            spinner_style=spinner_style,
            speed=speed,
            refresh_per_second=refresh_per_second,
        )

    def update(self, status: RenderableType) -> None:
        """Update the status with indenting."""
        super().update(Padding.indent(status, self.indent - 2))


class _Console(Console):
    """Add utilities to indent output."""

    def __init__(self, *args, indent: int = _INDENT, **kwargs):
        super().__init__(*args, **kwargs)
        self.indent = indent

    def confirm(
        self,
        prompt: str,
        kwargs_init: Optional[dict] = None,
        kwargs_call: Optional[dict] = None,
    ) -> bool:
        """
        Prompt for confirmation with indenting.

        This function creates a new _Confirm object with the given prompt and
        then calls it.
        """
        kwargs_init = kwargs_init or {}
        kwargs_call = kwargs_call or {}
        return _Confirm(prompt, console=self, indent=self.indent, **kwargs_init)(
            **kwargs_call
        )

    @_force_indent_if_internal
    def print(
        self,
        *renderables: Iterable[RenderableType],
        with_indent: bool = False,
        **kwargs,
    ) -> None:
        """Print an object with optional indenting."""
        if with_indent and len(renderables) == 1:
            renderables = (Padding.indent(renderables[0], self.indent),)
        super().print(*renderables, **kwargs)

    def status(self, status, **kwargs) -> _Status:
        """Override status to use indenting."""
        return _Status(
            status=status,
            console=self,
            indent=self.indent,
            **kwargs,
        )


CONSOLE_STDOUT = _Console(stderr=False, indent=_INDENT)
CONSOLE_STDERR = _Console(stderr=True, indent=_INDENT)
