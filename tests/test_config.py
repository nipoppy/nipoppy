"""Tests for the config module."""

import json
from pathlib import Path

import pytest
from conftest import DPATH_TEST_DATA
from pydantic import ValidationError

from nipoppy.config import Config, PipelineConfig, SingularityConfig, load_config
from nipoppy.utils import FPATH_SAMPLE_CONFIG

REQUIRED_FIELDS_CONFIG = ["DATASET_NAME", "SESSIONS", "PROC_PIPELINES"]
FIELDS_PIPELINE = [
    "CONTAINER",
    "URI",
    "SINGULARITY_CONFIG",
    "DESCRIPTOR",
    "INVOCATION",
    "PYBIDS_IGNORE",
]
FIELDS_SINGULARITY = ["COMMAND", "ARGS", "ENV_VARS"]


@pytest.fixture(scope="function")
def valid_config_data():
    return {
        "DATASET_NAME": "my_dataset",
        "SESSIONS": ["ses-1"],
        "BIDS": {
            "bids_converter": {"1.0": {"CONTAINER": "path"}},
        },
        "PROC_PIPELINES": {
            "pipeline1": {"v1": {}, "v2": {"CONTAINER": "path"}},
            "pipeline2": {"1.0": {"URI": "uri"}, "2.0": {"INVOCATION": {}}},
        },
    }


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"COMMAND": "apptainer"},
        {"ARGS": ["--cleanenv", "-H /my/path"]},
        {"ENV_VARS": {"TEMPLATEFLOW_HOME": "/path/to/templateflow"}},
    ],
)
def test_singularity_config(data):
    for field in FIELDS_SINGULARITY:
        assert hasattr(SingularityConfig(**data), field)


def test_singularity_config_no_extra_fields():
    with pytest.raises(ValidationError):
        SingularityConfig(not_a_field="a")


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"CONTAINER": "/my/container"},
        {"URI": "docker://container"},
        {"SINGULARITY_CONFIG": {"ARGS": ["--cleanenv"]}},
        {"DESCRIPTOR": "/my/descriptor"},
        {"INVOCATION": {"arg1": "val1", "arg2": "val2"}},
        {"PYBIDS_IGNORE": ["ignore1", "ignore2"]},
        {"DESCRIPTION": "My pipeline"},
    ],
)
def test_pipeline_config(data):
    for field in FIELDS_PIPELINE:
        assert hasattr(PipelineConfig(**data), field)


def test_pipeline_config_no_extra_fields():
    with pytest.raises(ValidationError):
        PipelineConfig(not_a_field="a")


@pytest.mark.parametrize("field_name", ["not_a_field", "also_not_a_field"])
def test_config_extra_fields_allowed(field_name, valid_config_data):
    args = valid_config_data
    args[field_name] = "extra"
    assert hasattr(Config(**args), field_name)


def test_config_no_duplicate_pipeline(valid_config_data):
    data = valid_config_data
    data["PROC_PIPELINES"].update(data["BIDS"])
    with pytest.raises(ValidationError):
        Config(**data)


@pytest.mark.parametrize(
    "pipeline,version",
    [("pipeline1", "v1"), ("pipeline2", "2.0"), ("bids_converter", "1.0")],
)
def test_config_get_pipeline_config(pipeline, version, valid_config_data):
    assert isinstance(
        Config(**valid_config_data).get_pipeline_config(pipeline, version),
        PipelineConfig,
    )


def test_config_get_pipeline_config_missing(valid_config_data):
    with pytest.raises(ValueError):
        Config(**valid_config_data).get_pipeline_config("not_a_pipeline", "v1")


def test_config_save(tmp_path: Path, valid_config_data):
    fpath_out = tmp_path / "config.json"
    config = Config(**valid_config_data)
    config.save(fpath_out)
    assert fpath_out.exists()
    with fpath_out.open("r") as file:
        assert isinstance(json.load(file), dict)


@pytest.mark.parametrize(
    "path",
    [
        FPATH_SAMPLE_CONFIG,
        DPATH_TEST_DATA / "config1.json",
        DPATH_TEST_DATA / "config2.json",
    ],
)
def test_load_config(path):
    config = load_config(path)
    assert isinstance(config, Config)
    for field in REQUIRED_FIELDS_CONFIG:
        assert hasattr(config, field)


def test_load_config_missing_required():
    with pytest.raises(ValueError):
        load_config(DPATH_TEST_DATA / "config3-invalid.json")
