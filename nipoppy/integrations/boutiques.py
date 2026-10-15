"""Integration layer for the Boutiques Python API."""

from __future__ import annotations

import importlib.metadata
from abc import ABC, abstractmethod
from pathlib import Path

import boutiques
from boutiques.util.utils import LoadError
from packaging.version import Version

from nipoppy.exceptions import ConfigError
from nipoppy.utils.utils import StrOrPathLike

BOUTIQUES_NEXT_VERSION = Version("0.6.0")


class BoutiquesAPI(ABC):
    """Interface for the Boutiques Python API."""

    @abstractmethod
    def validate_descriptor(self, descriptor: StrOrPathLike, /) -> None:
        """Validate a descriptor.

        Parameters
        ----------
        descriptor : StrOrPathLike
            The descriptor as a JSON string, or the path to a descriptor file.

        Raises
        ------
        ConfigError
            If the descriptor is invalid.
        """
        ...

    @abstractmethod
    def validate_invocation(
        self, invocation: StrOrPathLike, *, descriptor: StrOrPathLike
    ) -> None:
        """Validate an invocation against a descriptor.

        Parameters
        ----------
        invocation : StrOrPathLike
            The invocation as a JSON string, or the path to an invocation file.
        descriptor : StrOrPathLike
            The descriptor as a JSON string, or the path to a descriptor file.

        Raises
        ------
        ConfigError
            If the invocation is invalid or if the descriptor cannot be loaded.
        """
        ...

    @abstractmethod
    def create_descriptor(self, descriptor_path: Path, /) -> None:
        """Create an example descriptor.

        Parameters
        ----------
        output_path : Path
            Path where the descriptor should be written.
        """
        ...

    @abstractmethod
    def generate_example_invocation(self, descriptor_path: Path, /) -> str:
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

    def validate_descriptor(self, descriptor: StrOrPathLike, /) -> None:  # noqa: D102
        descriptor = str(descriptor)
        try:
            boutiques.validate(descriptor)
        except (
            boutiques.DescriptorValidationError,
            LoadError,
        ) as exception:
            raise ConfigError(
                f"Descriptor {descriptor} is invalid: {str(exception)}"
            ) from exception

    def validate_invocation(  # noqa: D102
        self, invocation: StrOrPathLike, *, descriptor: StrOrPathLike
    ) -> None:
        invocation = str(invocation)
        descriptor = str(descriptor)
        self.validate_descriptor(descriptor)
        try:
            boutiques.invocation("--invocation", invocation, descriptor)
        except (
            boutiques.InvocationValidationError,
            LoadError,
        ) as exception:
            raise ConfigError(
                f"Invocation {invocation} is invalid: {str(exception)}"
            ) from exception

    def create_descriptor(self, descriptor_path: Path, /) -> None:  # noqa: D102
        boutiques.create(str(descriptor_path))

    def generate_example_invocation(  # noqa: D102
        self, descriptor_path: Path, /
    ) -> str:
        return boutiques.example(str(descriptor_path))


class BoutiquesNextAPI(BoutiquesAPI):
    """Boutiques API for versions >= 0.6.0."""

    def validate_descriptor(self, descriptor: StrOrPathLike, /) -> None:  # noqa: D102
        raise NotImplementedError("boutiques >= 0.6.0 is not supported yet")

    def validate_invocation(  # noqa: D102
        self, invocation: StrOrPathLike, *, descriptor: StrOrPathLike
    ) -> None:
        raise NotImplementedError("boutiques >= 0.6.0 is not supported yet")

    def create_descriptor(self, descriptor_path: Path, /) -> None:  # noqa: D102
        raise NotImplementedError("boutiques >= 0.6.0 is not supported yet")

    def generate_example_invocation(  # noqa: D102
        self, descriptor_path: Path, /
    ) -> str:
        raise NotImplementedError("boutiques >= 0.6.0 is not supported yet")


def _create_boutiques_api() -> BoutiquesAPI:
    """Return a :class:`BoutiquesAPI` matching the installed ``boutiques`` version.

    Returns
    -------
    BoutiquesAPI

    Raises
    ------
    NotImplementedError
        If the installed ``boutiques`` version is not supported yet.
    """
    version = importlib.metadata.version("boutiques")
    if Version(version) < BOUTIQUES_NEXT_VERSION:
        return BoutiquesLegacyAPI()
    else:
        return BoutiquesNextAPI()


boutiques_api = _create_boutiques_api()
