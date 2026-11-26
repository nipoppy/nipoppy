"""Unit tests for the Boutiques Python API integration."""

import importlib.metadata
import json
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.exceptions import ConfigError
from nipoppy.integrations.boutiques import (
    BoutiquesAPI,
    BoutiquesFile,
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


class TestBoutiquesFile:
    def test_init_none_specified(self):
        with pytest.raises(ValueError, match="Either path or content must be provided"):
            BoutiquesFile()

    def test_init_both_specified(self):
        with pytest.raises(
            ValueError,
            match="Only one of path or content can be provided, got",
        ):
            BoutiquesFile(path=Path("descriptor.json"), content="{}")

    @pytest.mark.parametrize(
        "relative_path",
        [
            Path("descriptor.json"),
            Path("subdir/descriptor.json"),
        ],
    )
    def test_resolved_content_from_path(self, relative_path: Path, tmp_path: Path):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True)

        content = '{"name": "test_app"}'
        path.write_text(content)

        boutiques_file = BoutiquesFile(path=relative_path)
        assert boutiques_file.resolved_content == content

    @pytest.mark.parametrize(
        "content",
        [
            '{"name": "test_app"}',
            '{"inputs": [{"id": "input_file", "type": "File"}]}',
        ],
    )
    def test_resolved_content_from_content(self, content: str):
        boutiques_file = BoutiquesFile(content=content)
        assert boutiques_file.resolved_content == content

    def test_resolved_content_file_not_found(self, tmp_path: Path):
        path = tmp_path / "nonexistent.json"
        assert not path.exists()

        boutiques_file = BoutiquesFile(path=path)

        with pytest.raises(FileNotFoundError, match=f"File not found: {path}"):
            boutiques_file.resolved_content

    @pytest.mark.parametrize(
        ("relative_path", "content", "expected_str"),
        [
            ("descriptor.json", None, "descriptor.json"),
            (None, '{"name": "test_app"}', '{"name": "test_app"}'),
        ],
    )
    def test_str(
        self,
        relative_path: Path | None,
        content: str | None,
        expected_str: str,
        tmp_path: Path,
    ):
        if relative_path is not None:
            path = tmp_path / relative_path
        else:
            path = None
        boutiques_file_from_path = BoutiquesFile(path=path, content=content)
        assert str(boutiques_file_from_path) == expected_str


class TestBoutiquesAPI:
    def test_validate_descriptor(self, descriptor_str: str):
        boutiques_api.validate_descriptor(descriptor_str)

    def test_validate_descriptor_error(self):
        invalid_descriptor_str = json.dumps({"name": "test_app"})

        with pytest.raises(ConfigError, match="Descriptor .* is invalid"):
            boutiques_api.validate_descriptor(invalid_descriptor_str)

    def test_validate_invocation(self, descriptor_str: str, invocation_str: str):
        boutiques_api.validate_invocation(invocation_str, descriptor=descriptor_str)

    def test_validate_invocation_error(self, descriptor_str: str):
        invalid_invocation_str = json.dumps({"invalid_key": "value"})

        with pytest.raises(ConfigError, match="Invocation .* is invalid"):
            boutiques_api.validate_invocation(
                invalid_invocation_str, descriptor=descriptor_str
            )

    def test_generate_example_invocation(self, descriptor_str: str, tmp_path: Path):
        descriptor_path = tmp_path / "descriptor.json"
        descriptor_path.write_text(descriptor_str)

        invocation_str = boutiques_api.generate_example_invocation(descriptor_path)

        boutiques_api.validate_invocation(invocation_str, descriptor=descriptor_str)


class TestCreateBoutiquesAPI:
    @pytest.mark.parametrize(
        ("version", "api_class"),
        [("0.5.31", BoutiquesLegacyAPI), ("0.6.0", BoutiquesNextAPI)],
    )
    def test_create_boutiques_api(
        self,
        version: str,
        api_class: type[BoutiquesAPI],
        mocker: pytest_mock.MockerFixture,
    ):
        mocker.patch.object(importlib.metadata, "version", return_value=version)

        api = _create_boutiques_api()

        assert isinstance(api, api_class)
