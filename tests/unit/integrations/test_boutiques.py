"""Unit tests for the Boutiques Python API integration."""

import importlib.metadata
import json
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.integrations.boutiques import (
    BOUTIQUES_API,
    BoutiquesAPI,
    BoutiquesLegacyAPI,
    DescriptorValidationError,
    InvocationValidationError,
    _create_boutiques_api,
)


@pytest.fixture
def boutiques_api() -> BoutiquesLegacyAPI:
    """Return a Boutiques API object for testing."""
    return BoutiquesLegacyAPI()


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


def test_boutiques_api_abstract():
    with pytest.raises(TypeError):
        BoutiquesAPI()


@pytest.mark.parametrize("version", ["0.5.31", "0.5.33"])
def test_create_boutiques_api(version: str, mocker: pytest_mock.MockerFixture):
    mocker.patch.object(importlib.metadata, "version", return_value=version)

    api = _create_boutiques_api()

    assert isinstance(api, BoutiquesLegacyAPI)
    assert isinstance(api, BoutiquesAPI)


def test_create_boutiques_api_unsupported(mocker: pytest_mock.MockerFixture):
    mocker.patch.object(importlib.metadata, "version", return_value="0.6.0")

    with pytest.raises(NotImplementedError, match="not supported"):
        _create_boutiques_api()


def test_boutiques_api_global_is_instance():
    assert isinstance(BOUTIQUES_API, BoutiquesAPI)


def test_validate_descriptor(boutiques_api: BoutiquesLegacyAPI, descriptor_str: str):
    assert boutiques_api.validate_descriptor(descriptor_str) == descriptor_str


def test_validate_descriptor_error(boutiques_api: BoutiquesLegacyAPI):
    invalid_descriptor_str = json.dumps({"name": "test_app"})

    with pytest.raises(DescriptorValidationError):
        boutiques_api.validate_descriptor(invalid_descriptor_str)


def test_validate_invocation(
    boutiques_api: BoutiquesLegacyAPI,
    descriptor_str: str,
    invocation_str: str,
):
    boutiques_api.validate_invocation(descriptor_str, invocation_str)


def test_validate_invocation_error(
    boutiques_api: BoutiquesLegacyAPI, descriptor_str: str
):
    invalid_invocation_str = json.dumps({"invalid_key": "value"})

    with pytest.raises(InvocationValidationError):
        boutiques_api.validate_invocation(descriptor_str, invalid_invocation_str)


def test_create_descriptor(boutiques_api: BoutiquesLegacyAPI, tmp_path: Path):
    output_path = tmp_path / "descriptor.json"

    boutiques_api.create_descriptor(output_path)

    boutiques_api.validate_descriptor(output_path.read_text())


def test_generate_example_invocation(
    boutiques_api: BoutiquesLegacyAPI,
    descriptor_str: str,
    tmp_path: Path,
):
    descriptor_path = tmp_path / "descriptor.json"
    descriptor_path.write_text(descriptor_str)

    example_invocation = boutiques_api.generate_example_invocation(descriptor_path)

    assert isinstance(json.loads(example_invocation), dict)
