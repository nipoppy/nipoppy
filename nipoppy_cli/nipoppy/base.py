"""Base class."""

import inspect
from abc import ABC
from typing import Optional, Sequence


class Base(ABC):
    """Base class with utilities for pretty string representations."""

    def _str_helper(
        self,
        components: Optional[Sequence] = None,
        names: Optional[Sequence[str]] = None,
        sep=", ",
    ) -> str:
        """Generate a custom string representation of an object.

        The output string is of the form: ClassName(component1[sep]component2[sep]...)

        Parameters
        ----------
        components : Sequence, optional
            Components to concatenate, by default None
        names : Sequence[str], optional
            Name of attributes to be added to the components as key-value pairs,
            by default None
        sep : str, optional
            Separator between components, by default ", "

        Returns
        -------
        str
            String representation of the object.
        """
        if components is None:
            components = []

        if names is not None:
            for name in names:
                components.append(f"{name}={getattr(self, name)}")

        return f"{type(self).__name__}({sep.join([str(c) for c in components])})"

    def __str__(self) -> str:
        """Return a string representation of the object based on its __init__ arguments.

        Raises
        ------
        RuntimeError
            If the parameter names obtained from the __init__ method do not match the
            attributes of the object.
        """
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
