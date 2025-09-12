"""Tests for container configuration."""

import pytest
from pydantic import ValidationError

from nipoppy.config.container import (
    ContainerConfig,
    ContainerInfo,
    _SchemaWithContainerConfig,
    prepare_container,
)

FIELDS_CONTAINER_CONFIG = [
    "COMMAND",
    "ARGS",
    "ENV_VARS",
    "INHERIT",
]

FIELDS_CONTAINER_INFO = ["FILE", "URI"]


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"COMMAND": "apptainer"},
        {"ARGS": ["--cleanenv", "-H /my/path"]},
        {"ENV_VARS": {"TEMPLATEFLOW_HOME": "/path/to/templateflow"}},
    ],
)
def test_container_config(data):
    container_config = ContainerConfig(**data)
    for field in FIELDS_CONTAINER_CONFIG:
        assert hasattr(container_config, field)
    assert len(container_config.model_dump()) == len(FIELDS_CONTAINER_CONFIG)


@pytest.mark.parametrize(
    "data1,data2,data_expected",
    [
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"]},
            {"ARGS": ["--cleanenv", "--fakeroot"]},
        ),
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--cleanenv"]},
        ),
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--cleanenv", "--fakeroot"]},
            {"ARGS": ["--cleanenv", "--cleanenv", "--fakeroot"]},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR2": "2"}},
            {"ENV_VARS": {"VAR1": "1", "VAR2": "2"}},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR1": "111", "VAR2": "2"}},
            {"ENV_VARS": {"VAR1": "1", "VAR2": "2"}},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR1": "1"}},
        ),
    ],
)
def test_container_config_merge(data1, data2, data_expected):
    merged = ContainerConfig(**data1).merge(ContainerConfig(**data2))
    assert merged == ContainerConfig(**data_expected)


@pytest.mark.parametrize(
    "data1,data2,overwrite_command,data_expected",
    [
        (
            {"COMMAND": "apptainer"},
            {"COMMAND": "singularity"},
            True,
            {"COMMAND": "singularity"},
        ),
        (
            {"COMMAND": "apptainer"},
            {"COMMAND": "singularity"},
            False,
            {"COMMAND": "apptainer"},
        ),
    ],
)
def test_container_config_merge_overwrite_command(
    data1, data2, overwrite_command, data_expected
):
    merged = ContainerConfig(**data1).merge(
        ContainerConfig(**data2), overwrite_command=overwrite_command
    )
    assert merged == ContainerConfig(**data_expected)


def test_container_config_merge_error():
    with pytest.raises(TypeError, match="Cannot merge"):
        ContainerConfig().merge("bad_arg")


def test_container_config_no_extra_fields():
    with pytest.raises(ValidationError):
        ContainerConfig(not_a_field="a")


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"FILE": "path/to/container.sif"},
        {"FILE": "path/to/container.sif", "URI": "docker://my/container"},
    ],
)
def test_container_info(data):
    container_info = ContainerInfo(**data)
    for field in FIELDS_CONTAINER_INFO:
        assert hasattr(container_info, field)
    assert len(container_info.model_dump()) == len(FIELDS_CONTAINER_INFO)


def test_container_info_no_extra_fields():
    with pytest.raises(ValidationError):
        ContainerInfo(not_a_field="a")


def test_container_info_file_exists_if_uri_exists():
    with pytest.raises(ValidationError, match="FILE must be specified if URI is set"):
        ContainerInfo(URI="docker://my/container")


def test_schema_with_container_config():
    class ClassWithContainerConfig(_SchemaWithContainerConfig):
        pass

    assert isinstance(
        ClassWithContainerConfig(a=1, b=2).get_container_config(),
        ContainerConfig,
    )


@pytest.mark.parametrize(
    "data, expected",
    [
        ({}, "apptainer run"),
        (
            {
                "COMMAND": "singularity",
                "ARGS": ["--cleanenv"],
            },
            "singularity run --cleanenv",
        ),
    ],
)
def test_prepare_container(data, expected):
    assert prepare_container(ContainerConfig(**data), check=False) == expected


def test_prepare_container_error():
    with pytest.raises(ValueError, match="COMMAND cannot be None"):
        prepare_container(ContainerConfig(COMMAND=None), check=False)
