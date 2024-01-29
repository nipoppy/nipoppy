"""Base class."""


class _Base:
    """Base class with utilities for pretty printing."""

    def _str_helper(self, components=None, names=None, sep=", "):
        if components is None:
            components = []

        if names is not None:
            for name in names:
                components.append(f"{name}={getattr(self, name)}")
        return f"{type(self).__name__}({sep.join([str(c) for c in components])})"

    def __str__(self) -> str:
        return self._str_helper()

    def __repr__(self) -> str:
        return self.__str__()
