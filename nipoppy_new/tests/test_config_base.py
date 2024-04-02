"""Tests for the config module."""

import json
from pathlib import Path

import pytest
from conftest import DPATH_TEST_DATA
from pydantic import ValidationError

from nipoppy.config.base import Config
from nipoppy.config.pipeline import PipelineConfig
from nipoppy.config.singularity import SingularityConfig
from nipoppy.utils import FPATH_SAMPLE_CONFIG

REQUIRED_FIELDS_CONFIG = ["DATASET_NAME", "SESSIONS", "PROC_PIPELINES"]


@pytest.fixture(scope="function")
def valid_config_data():
    return {
        "DATASET_NAME": "my_dataset",
        "SESSIONS": ["ses-1"],
        "BIDS": {
            "bids_converter": {
                "1.0": {
                    "step1": {"CONTAINER": "path"},
                    "step2": {"CONTAINER": "other_path"},
                }
            },
        },
        "PROC_PIPELINES": {
            "pipeline1": {"v1": {}, "v2": {"CONTAINER": "path"}},
            "pipeline2": {"1.0": {"URI": "uri"}, "2.0": {"INVOCATION": {}}},
        },
    }


@pytest.mark.parametrize("field_name", ["not_a_field", "also_not_a_field"])
def test_extra_fields_allowed(field_name, valid_config_data):
    args = valid_config_data
    args[field_name] = "extra"
    assert hasattr(Config(**args), field_name)


def test_check_no_duplicate_pipeline(valid_config_data):
    data: dict = valid_config_data
    data["PROC_PIPELINES"].update(data["BIDS"])
    with pytest.raises(ValidationError):
        Config(**data)


@pytest.mark.parametrize(
    "data_root,data_pipeline,data_expected",
    [
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"]},
            {"ARGS": ["--fakeroot", "--cleanenv"]},
        ),
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"], "INHERIT": "false"},
            {"ARGS": ["--fakeroot"], "INHERIT": "false"},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR2": "2"}},
            {"ENV_VARS": {"VAR1": "1", "VAR2": "2"}},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR2": "2"}, "INHERIT": "false"},
            {"ENV_VARS": {"VAR2": "2"}, "INHERIT": "false"},
        ),
    ],
)
def test_propagate_singularity_config(data_root, data_pipeline, data_expected):
    pipeline_name = "pipeline1"
    pipeline_version = "1.0"
    data = {
        "DATASET_NAME": "my_dataset",
        "SESSIONS": [],
        "SINGULARITY_CONFIG": data_root,
        "BIDS": {},
        "PROC_PIPELINES": {
            pipeline_name: {pipeline_version: {"SINGULARITY_CONFIG": data_pipeline}}
        },
    }

    singularity_config = (
        Config(**data)
        .get_pipeline_config(pipeline_name, pipeline_version)
        .get_singularity_config()
    )

    assert singularity_config == SingularityConfig(**data_expected)


@pytest.mark.parametrize(
    "data_root,data_pipeline,data_expected",
    [
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"]},
            {"ARGS": ["--fakeroot", "--cleanenv"]},
        ),
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"], "INHERIT": "false"},
            {"ARGS": ["--fakeroot"], "INHERIT": "false"},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR2": "2"}},
            {"ENV_VARS": {"VAR1": "1", "VAR2": "2"}},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR2": "2"}, "INHERIT": "false"},
            {"ENV_VARS": {"VAR2": "2"}, "INHERIT": "false"},
        ),
    ],
)
def test_propagate_singularity_config_bids(data_root, data_pipeline, data_expected):
    pipeline_name = "pipeline1"
    pipeline_version = "1.0"
    step_name = "step1"
    data = {
        "DATASET_NAME": "my_dataset",
        "SESSIONS": [],
        "SINGULARITY_CONFIG": data_root,
        "BIDS": {
            pipeline_name: {
                pipeline_version: {step_name: {"SINGULARITY_CONFIG": data_pipeline}}
            }
        },
        "PROC_PIPELINES": {},
    }

    singularity_config = (
        Config(**data)
        .get_bids_pipeline_config(pipeline_name, pipeline_version, step_name)
        .get_singularity_config()
    )

    assert singularity_config == SingularityConfig(**data_expected)


@pytest.mark.parametrize(
    "pipeline,version",
    [("pipeline1", "v1"), ("pipeline2", "2.0")],
)
def test_get_pipeline_config(pipeline, version, valid_config_data):
    assert isinstance(
        Config(**valid_config_data).get_pipeline_config(pipeline, version),
        PipelineConfig,
    )


@pytest.mark.parametrize(
    "pipeline,version,step",
    [("bids_converter", "1.0", "step1"), ("bids_converter", "1.0", "step2")],
)
def test_get_bids_pipeline_config(pipeline, version, step, valid_config_data):
    assert isinstance(
        Config(**valid_config_data).get_bids_pipeline_config(pipeline, version, step),
        PipelineConfig,
    )


def test_get_pipeline_config_missing(valid_config_data):
    with pytest.raises(ValueError):
        Config(**valid_config_data).get_pipeline_config("not_a_pipeline", "v1")


def test_save(tmp_path: Path, valid_config_data):
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
def test_load(path):
    config = Config.load(path)
    assert isinstance(config, Config)
    for field in REQUIRED_FIELDS_CONFIG:
        assert hasattr(config, field)


def test_load_missing_required():
    with pytest.raises(ValueError):
        Config.load(DPATH_TEST_DATA / "config3-invalid.json")
