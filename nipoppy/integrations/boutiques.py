"""Integration layer for the Boutiques Python API."""

from __future__ import annotations

import importlib.metadata
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import ClassVar

import boutiques
from boutiques.util.utils import LoadError
from packaging.version import Version

from nipoppy.exceptions import ConfigError, FileOperationError
from nipoppy.utils.utils import load_json

BOUTIQUES_NEXT_VERSION = Version("0.6.0")


@dataclass(frozen=True)
class BoutiquesFile:
    """Representation of a Boutiques descriptor or invocation."""

    path: Path | None = None
    content: str | None = None
    allow_json5: ClassVar[bool] = False

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
                raise FileOperationError(f"File not found: {self.path}")
            return json.dumps(load_json(self.path, allow_json5=self.allow_json5))
        else:
            return self.content

    def __str__(self) -> str:
        if self.path is not None:
            return str(self.path)
        return self.resolved_content


@dataclass(frozen=True)
class DescriptorFile(BoutiquesFile):
    """Representation of a Boutiques descriptor file."""

    allow_json5: ClassVar[bool] = False


@dataclass(frozen=True)
class InvocationFile(BoutiquesFile):
    """Representation of a Boutiques invocation file."""

    allow_json5: ClassVar[bool] = True


class BoutiquesAPI(ABC):
    """Interface for the Boutiques Python API."""

    @abstractmethod
    def validate_descriptor(self, descriptor: DescriptorFile, /) -> None:
        """Validate a descriptor.

        Raises
        ------
        ConfigError
            If the descriptor is invalid.
        """
        ...

    @abstractmethod
    def validate_invocation(
        self, invocation: InvocationFile, *, descriptor: DescriptorFile
    ) -> None:
        """Validate an invocation against a descriptor.

        Raises
        ------
        ConfigError
            If the invocation is invalid or if the descriptor cannot be loaded.
        """
        ...

    @abstractmethod
    def generate_example_invocation(self, descriptor: DescriptorFile, /) -> str:
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

    def validate_descriptor(self, descriptor: DescriptorFile, /) -> None:  # noqa: D102
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
        self, invocation: InvocationFile, *, descriptor: DescriptorFile
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

    def generate_example_invocation(  # noqa: D102
        self, descriptor: DescriptorFile, /
    ) -> str:
        self.validate_descriptor(descriptor)
        return boutiques.example(str(descriptor))


class BoutiquesNextAPI(BoutiquesAPI):
    """Boutiques API for versions >= 0.6.0."""

    def validate_descriptor(self, descriptor: DescriptorFile, /) -> None:  # noqa: D102
        raise NotImplementedError(
            f"boutiques >= {BOUTIQUES_NEXT_VERSION} is not supported yet"
        )

    def validate_invocation(  # noqa: D102
        self, invocation: InvocationFile, *, descriptor: DescriptorFile
    ) -> None:
        raise NotImplementedError(
            f"boutiques >= {BOUTIQUES_NEXT_VERSION} is not supported yet"
        )

    def generate_example_invocation(  # noqa: D102
        self, descriptor: DescriptorFile, /
    ) -> str:
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
