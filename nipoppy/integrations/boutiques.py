"""Integration layer for the Boutiques Python API."""

from __future__ import annotations

import importlib.metadata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import boutiques
from boutiques.util.utils import LoadError
from packaging.version import Version

from nipoppy.exceptions import ConfigError

BOUTIQUES_NEXT_VERSION = Version("0.6.0")


@dataclass(frozen=True)
class BoutiquesFile:
    """Representation of a Boutiques descriptor or invocation."""

    path: Path | None = None
    content: str | None = None

    def __post_init__(self) -> None:

        if self.path is None and self.content is None:
            raise ValueError("Either path or content must be provided.")
        if self.path is not None and self.content is not None:
            raise ValueError(
                f"Only one of path or content can be provided, got {self.path=} and {self.content=}."  # noqa: E501
            )

    @cached_property
    def resolved_content(self) -> str:
        """The resolved content of the descriptor or invocation."""
        if self.path is not None:
            if not self.path.exists():
                raise FileNotFoundError(f"File not found: {self.path}")
            return self.path.read_text()
        return self.content

    def __str__(self) -> str:
        if self.path is not None:
            return str(self.path)
        return self.resolved_content


class BoutiquesAPI(ABC):
    """Interface for the Boutiques Python API."""

    @abstractmethod
    def validate_descriptor(self, descriptor: BoutiquesFile, /) -> None:
        """Validate a descriptor.

        Raises
        ------
        ConfigError
            If the descriptor is invalid.
        """
        ...

    @abstractmethod
    def validate_invocation(
        self, invocation: BoutiquesFile, *, descriptor: BoutiquesFile
    ) -> None:
        """Validate an invocation against a descriptor.

        Raises
        ------
        ConfigError
            If the invocation is invalid or if the descriptor cannot be loaded.
        """
        ...

    @abstractmethod
    def generate_example_invocation(self, descriptor: BoutiquesFile, /) -> str:
        """Generate an example invocation for a descriptor.

        Parameters
        ----------
        descriptor_path : Path
            Path to the descriptor file.

        Returns
        -------
        str
            The example invocation as a JSON string.
        """
        ...


class BoutiquesLegacyAPI(BoutiquesAPI):
    """Boutiques API for versions < 0.6.0."""

    def validate_descriptor(self, descriptor: BoutiquesFile, /) -> None:  # noqa: D102
        try:
            boutiques.validate(str(descriptor))
        except (
            boutiques.DescriptorValidationError,
            LoadError,
        ) as exception:
            raise ConfigError(
                f"Descriptor {descriptor} is invalid: run `bosh validate` for more details"  # noqa: E501
            ) from exception

    def validate_invocation(  # noqa: D102
        self, invocation: BoutiquesFile, *, descriptor: BoutiquesFile
    ) -> None:
        self.validate_descriptor(descriptor)
        try:
            boutiques.invocation("--invocation", str(invocation), str(descriptor))
        except (
            boutiques.InvocationValidationError,
            LoadError,
        ) as exception:
            raise ConfigError(
                f"Invocation {invocation} is invalid: {str(exception)}"
            ) from exception

    def generate_example_invocation(self, descriptor: BoutiquesFile, /) -> str:  # noqa: D102
        self.validate_descriptor(descriptor)
        return boutiques.example(str(descriptor))


class BoutiquesNextAPI(BoutiquesAPI):
    """Boutiques API for versions >= 0.6.0."""

    def validate_descriptor(self, descriptor: BoutiquesFile, /) -> None:  # noqa: D102
        raise NotImplementedError(
            f"boutiques >= {BOUTIQUES_NEXT_VERSION} is not supported yet"
        )

    def validate_invocation(  # noqa: D102
        self, invocation: BoutiquesFile, *, descriptor: BoutiquesFile
    ) -> None:
        raise NotImplementedError(
            f"boutiques >= {BOUTIQUES_NEXT_VERSION} is not supported yet"
        )

    def generate_example_invocation(self, descriptor: BoutiquesFile, /) -> str:  # noqa: D102
        raise NotImplementedError(
            f"boutiques >= {BOUTIQUES_NEXT_VERSION} is not supported yet"
        )


def _create_boutiques_api() -> BoutiquesAPI:
    """Return a :class:`BoutiquesAPI` matching the installed ``boutiques`` version.

    Returns
    -------
    BoutiquesAPI

    """
    version = importlib.metadata.version("boutiques")
    if Version(version) < BOUTIQUES_NEXT_VERSION:
        return BoutiquesLegacyAPI()
    else:
        return BoutiquesNextAPI()


boutiques_api = _create_boutiques_api()
