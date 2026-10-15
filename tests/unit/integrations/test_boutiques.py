"""Unit tests for the Boutiques Python API integration."""

import importlib.metadata
import json
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.exceptions import ConfigError
from nipoppy.integrations.boutiques import (
    BoutiquesAPI,
    BoutiquesLegacyAPI,
    BoutiquesNextAPI,
    _create_boutiques_api,
    boutiques_api,
)


@pytest.fixture
def descriptor_str() -> str:
    """Return a valid Boutiques descriptor as a JSON string."""
    return json.dumps(
        {
            "name": "test_app",
            "description": "Test application",
            "schema-version": "0.5",
            "tool-version": "1.0.0",
            "command-line": "test_app [INPUT]",
            "inputs": [
                {
                    "id": "input_file",
                    "name": "Input File",
                    "type": "File",
                    "value-key": "[INPUT]",
                }
            ],
        }
    )


@pytest.fixture
def invocation_str() -> str:
    """Return a valid Boutiques invocation as a JSON string."""
    return json.dumps({"input_file": "/path/to/input.txt"})


@pytest.mark.parametrize(
    ("version", "api_class"),
    [("0.5.31", BoutiquesLegacyAPI), ("0.6.0", BoutiquesNextAPI)],
)
def test_create_boutiques_api(
    version: str, api_class: type[BoutiquesAPI], mocker: pytest_mock.MockerFixture
):
    mocker.patch.object(importlib.metadata, "version", return_value=version)

    api = _create_boutiques_api()

    assert isinstance(api, api_class)


def test_validate_descriptor(descriptor_str: str):
    boutiques_api.validate_descriptor(descriptor_str)


def test_validate_descriptor_error():
    invalid_descriptor_str = json.dumps({"name": "test_app"})

    with pytest.raises(ConfigError, match="Descriptor .* is invalid"):
        boutiques_api.validate_descriptor(invalid_descriptor_str)


def test_validate_invocation(
    descriptor_str: str,
    invocation_str: str,
):
    boutiques_api.validate_invocation(invocation_str, descriptor=descriptor_str)


def test_validate_invocation_error(descriptor_str: str):
    invalid_invocation_str = json.dumps({"invalid_key": "value"})

    with pytest.raises(ConfigError, match="Invocation .* is invalid"):
        boutiques_api.validate_invocation(
            invalid_invocation_str, descriptor=descriptor_str
        )


def test_create_descriptor(tmp_path: Path):
    output_path = tmp_path / "descriptor.json"

    boutiques_api.create_descriptor(output_path)

    boutiques_api.validate_descriptor(output_path.read_text())


def test_generate_example_invocation(descriptor_str: str, tmp_path: Path):
    descriptor_path = tmp_path / "descriptor.json"
    descriptor_path.write_text(descriptor_str)

    invocation_str = boutiques_api.generate_example_invocation(descriptor_path)

    boutiques_api.validate_invocation(invocation_str, descriptor=descriptor_str)
