"""Tests for container configuration."""

import pytest

from nipoppy.config.container import (
    ContainerConfig,
    ContainerInfo,
    _SchemaWithContainerConfig,
)

FIELDS_CONTAINER_CONFIG = [
    "COMMAND",
    "ARGS",
    "BIND_PATHS",
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
    with pytest.raises(ValueError):
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
    with pytest.raises(ValueError):
        ContainerInfo(not_a_field="a")


def test_container_info_file_exists_if_uri_exists():
    with pytest.raises(ValueError, match="FILE must be specified if URI is set"):
        ContainerInfo(URI="docker://my/container")


def test_schema_with_container_config():
    class ClassWithContainerConfig(_SchemaWithContainerConfig):
        pass

    assert isinstance(
        ClassWithContainerConfig(a=1, b=2).get_container_config(),
        ContainerConfig,
    )
