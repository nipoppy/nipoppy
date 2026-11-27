"""Unit tests for the Boutiques Python API integration."""

import importlib.metadata
import json
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.exceptions import ConfigError, FileOperationError, JSONError
from nipoppy.integrations.boutiques import (
    BoutiquesAPI,
    BoutiquesFile,
    BoutiquesLegacyAPI,
    BoutiquesNextAPI,
    DescriptorFile,
    InvocationFile,
    _create_boutiques_api,
    boutiques_api,
)


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
        path.parent.mkdir(parents=True, exist_ok=True)

        content = '{"name": "test_app"}'
        path.write_text(content)

        boutiques_file = BoutiquesFile(path=path)
        assert boutiques_file.resolved_content == content

    @pytest.mark.parametrize(
        "content",
        [
            '{"name": "test_app"}',
            '{"inputs": [{"id": "input_file", "type": "File"}]}',
        ],
    )
    def test_resolved_content_from_str_content(self, content: str):
        boutiques_file = BoutiquesFile(content=content)
        assert boutiques_file.resolved_content == content

    def test_resolved_content_file_not_found(self, tmp_path: Path):
        path = tmp_path / "nonexistent.json"
        assert not path.exists()

        boutiques_file = BoutiquesFile(path=path)

        with pytest.raises(FileOperationError, match=f"File not found: {path}"):
            boutiques_file.resolved_content

    @pytest.mark.parametrize(
        ("relative_path", "content", "expected_fstr"),
        [
            (Path("descriptor.json"), None, "{tmp_path}/descriptor.json"),
            (None, '{"name": "test_app"}', '{{"name": "test_app"}}'),
        ],
    )
    def test_str(
        self,
        relative_path: Path | None,
        content: str | None,
        expected_fstr: str,
        tmp_path: Path,
    ):
        if relative_path is not None:
            path = tmp_path / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}")
        else:
            path = None
        boutiques_file_from_path = BoutiquesFile(path=path, content=content)
        assert str(boutiques_file_from_path) == expected_fstr.format(tmp_path=tmp_path)


class TestDescriptorFile:
    def test_resolved_content_from_path_errors_with_json5(self, tmp_path: Path):
        path = tmp_path / "descriptor.json"
        content = "{name: 'test_app'}"  # Invalid JSON, valid JSON5 (single quotes)
        path.write_text(content)

        boutiques_file = DescriptorFile(path=path)

        with pytest.raises(
            JSONError,
            match=f"Expecting property name enclosed in double quotes: {path}",
        ):
            boutiques_file.resolved_content


class TestInvocationFile:
    def test_resolved_content_from_path_allows_json5(self, tmp_path: Path):
        path = tmp_path / "descriptor.json"
        content = "{name: 'test_app'}"  # Invalid JSON, valid JSON5 (single quotes)
        path.write_text(content)

        boutiques_file = InvocationFile(path=path)

        # valid
        assert boutiques_file.resolved_content == '{"name": "test_app"}'


class TestBoutiquesAPI:
    @pytest.fixture
    def descriptor_file(self) -> DescriptorFile:
        return DescriptorFile(
            content=json.dumps(
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
        )

    @pytest.fixture
    def invocation_file(self) -> InvocationFile:
        return InvocationFile(content=json.dumps({"input_file": "/path/to/input.txt"}))

    def test_validate_descriptor(self, descriptor_file: DescriptorFile):
        assert boutiques_api.validate_descriptor(descriptor_file) is descriptor_file

    @pytest.mark.parametrize(
        ("descriptor_file", "exception_class", "error_message"),
        [
            ("{}", TypeError, "Expected a DescriptorFile, got ."),
            (
                "descriptor.json",
                TypeError,
                "Expected a DescriptorFile, got .",
            ),
            (DescriptorFile(content="{}"), ConfigError, "Descriptor .* is invalid"),
        ],
    )
    def test_validate_descriptor_error(
        self,
        descriptor_file: DescriptorFile,
        exception_class: type[Exception],
        error_message: str,
    ):
        with pytest.raises(exception_class, match=error_message):
            boutiques_api.validate_descriptor(descriptor_file)

    def test_validate_invocation(
        self, invocation_file: InvocationFile, descriptor_file: DescriptorFile
    ):
        assert (
            boutiques_api.validate_invocation(
                invocation_file, descriptor=descriptor_file
            )
            is invocation_file
        )

    @pytest.mark.parametrize(
        ("invocation_file", "exception_class", "error_message"),
        [
            ("{}", TypeError, "Expected an InvocationFile, got ."),
            (
                "invocation.json",
                TypeError,
                "Expected an InvocationFile, got .",
            ),
            (
                InvocationFile(content='{"invalid_key": "value"}'),
                ConfigError,
                "Invocation .* is invalid",
            ),
        ],
    )
    def test_validate_invocation_error(
        self,
        invocation_file: InvocationFile,
        exception_class: type[Exception],
        error_message: str,
        descriptor_file: DescriptorFile,
    ):
        with pytest.raises(exception_class, match=error_message):
            boutiques_api.validate_invocation(
                invocation_file, descriptor=descriptor_file
            )

    def test_generate_example_invocation(self, descriptor_file: DescriptorFile):
        invocation_file = boutiques_api.generate_example_invocation(descriptor_file)
        assert (
            boutiques_api.validate_invocation(
                invocation_file, descriptor=descriptor_file
            )
            is invocation_file
        )


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
