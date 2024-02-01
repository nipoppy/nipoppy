"""Base class."""
import inspect
from abc import ABC


class _Base(ABC):
    """Base class with utilities for pretty printing."""

    def _str_helper(self, components=None, names=None, sep=", "):
        if components is None:
            components = []

        if names is not None:
            for name in names:
                components.append(f"{name}={getattr(self, name)}")
        return f"{type(self).__name__}({sep.join([str(c) for c in components])})"

    def __str__(self) -> str:
        signature = inspect.signature(type(self))
        names = [
            name
            for name, parameter in signature.parameters.items()
            if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        ]
        try:
            return self._str_helper(names=names)
        except AttributeError:
            raise RuntimeError(
                f"The __init__ method of the {type(self)} class has positional and/or"
                " keyword arguments that are not set as attributes of the object"
                ". Failed to build string representation: need to override the"
                " __str__ method"
            )

    def __repr__(self) -> str:
        return self.__str__()
