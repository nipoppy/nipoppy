"""Integration layer for the Boutiques Python API."""

from __future__ import annotations

import importlib.metadata
from abc import ABC, abstractmethod
from pathlib import Path

import boutiques
from packaging.version import Version


class BoutiquesAPIError(Exception):
    """Base exception for errors raised by the Boutiques API."""


class DescriptorValidationError(BoutiquesAPIError):
    """Raised when a Boutiques descriptor fails validation."""


class InvocationValidationError(BoutiquesAPIError):
    """Raised when a Boutiques invocation fails validation."""


class BoutiquesAPI(ABC):
    """Interface for the Boutiques Python API."""

    @abstractmethod
    def validate_descriptor(self, descriptor_str: str) -> str:
        """Validate a descriptor and return the validated descriptor string.

        Parameters
        ----------
        descriptor_str : str
            The Boutiques descriptor as a JSON string.

        Returns
        -------
        str
            The validated descriptor as a JSON string.

        Raises
        ------
        DescriptorValidationError
            If the descriptor is invalid.
        """
        ...

    @abstractmethod
    def validate_invocation(self, descriptor_str: str, invocation_str: str) -> None:
        """Validate an invocation against a descriptor.

        Parameters
        ----------
        descriptor_str : str
            The Boutiques descriptor as a JSON string.
        invocation_str : str
            The Boutiques invocation as a JSON string.

        Raises
        ------
        InvocationValidationError
            If the invocation is invalid.
        """
        ...

    @abstractmethod
    def create_descriptor(self, output_path: Path) -> None:
        """Create a starter descriptor template.

        Parameters
        ----------
        output_path : Path
            Path where the starter descriptor should be written.
        """
        ...

    @abstractmethod
    def generate_example_invocation(self, descriptor_path: Path) -> str:
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

    def validate_descriptor(self, descriptor_str: str) -> str:  # noqa: D102
        try:
            boutiques.validate(descriptor_str)
        except boutiques.DescriptorValidationError as exception:
            raise DescriptorValidationError(str(exception)) from exception
        return descriptor_str

    def validate_invocation(self, descriptor_str: str, invocation_str: str) -> None:  # noqa: D102
        try:
            boutiques.invocation("--invocation", invocation_str, descriptor_str)
        except boutiques.InvocationValidationError as exception:
            raise InvocationValidationError(str(exception)) from exception

    def create_descriptor(self, output_path: Path) -> None:  # noqa: D102
        boutiques.create(str(output_path))

    def generate_example_invocation(self, descriptor_path: Path) -> str:  # noqa: D102
        return boutiques.example(str(descriptor_path))


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
    if Version(version) < Version("0.6"):
        return BoutiquesLegacyAPI()
    raise NotImplementedError(f"boutiques version {version} is not supported yet.")


BOUTIQUES_API = _create_boutiques_api()
