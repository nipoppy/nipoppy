"""Tests for the config module."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from nipoppy.config.container import ContainerConfig
from nipoppy.config.main import Config
from nipoppy.config.pipeline import PipelineConfig
from nipoppy.utils import FPATH_SAMPLE_CONFIG

from .conftest import DPATH_TEST_DATA

REQUIRED_FIELDS_CONFIG = ["DATASET_NAME", "SESSIONS", "PROC_PIPELINES"]


@pytest.fixture(scope="function")
def valid_config_data():
    return {
        "DATASET_NAME": "my_dataset",
        "VISITS": ["1"],
        "SESSIONS": ["ses-1"],
        "BIDS_PIPELINES": [
            {
                "NAME": "bids_converter",
                "VERSION": "1.0",
                "STEP": "step1",
                "CONTAINER": "path",
            },
            {
                "NAME": "bids_converter",
                "VERSION": "1.0",
                "STEP": "step2",
                "CONTAINER": "other_path",
            },
        ],
        "PROC_PIPELINES": [
            {"NAME": "pipeline1", "VERSION": "v1"},
            {"NAME": "pipeline1", "VERSION": "v2", "CONTAINER": "path"},
            {"NAME": "pipeline2", "VERSION": "1.0", "URI": "uri"},
            {"NAME": "pipeline2", "VERSION": "2.0", "INVOCATION": {}},
        ],
    }


@pytest.mark.parametrize("field_name", ["not_a_field", "also_not_a_field"])
def test_extra_fields_allowed(field_name, valid_config_data):
    args = valid_config_data
    args[field_name] = "extra"
    assert hasattr(Config(**args), field_name)


@pytest.mark.parametrize(
    "proc_pipelines_data,bids_pipelines_data",
    [
        (
            [
                {"NAME": "pipeline1", "VERSION": "v1"},
                {"NAME": "pipeline1", "VERSION": "v1"},
            ],
            [],
        ),
        (
            [],
            [
                {"NAME": "pipeline1", "VERSION": "v1", "STEP": "step1"},
                {"NAME": "pipeline1", "VERSION": "v1", "STEP": "step1"},
            ],
        ),
    ],
)
def test_check_no_duplicate_pipeline(
    valid_config_data, proc_pipelines_data, bids_pipelines_data
):
    data: dict = valid_config_data
    data["PROC_PIPELINES"] = proc_pipelines_data
    data["BIDS_PIPELINES"] = bids_pipelines_data
    with pytest.raises(ValidationError, match="Found multiple configurations for"):
        Config(**data)


@pytest.mark.parametrize(
    "visits,expected_sessions",
    [
        (["V01", "V02"], ["ses-V01", "ses-V02"]),
        (["ses-1", "2"], ["ses-1", "ses-2"]),
    ],
)
def test_sessions_inferred(visits, expected_sessions):
    data = {
        "DATASET_NAME": "my_dataset",
        "VISITS": visits,
        "BIDS_PIPELINES": [],
        "PROC_PIPELINES": [],
    }
    config = Config(**data)
    assert config.SESSIONS == expected_sessions


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
def test_propagate_container_config(
    valid_config_data, data_root, data_pipeline, data_expected
):
    pipeline_name = "pipeline1"
    pipeline_version = "1.0"
    data = valid_config_data
    data["CONTAINER_CONFIG"] = data_root
    data["PROC_PIPELINES"] = [
        {
            "NAME": pipeline_name,
            "VERSION": pipeline_version,
            "CONTAINER_CONFIG": data_pipeline,
        }
    ]

    container_config = (
        Config(**data)
        .get_pipeline_config(pipeline_name, pipeline_version)
        .get_container_config()
    )

    assert container_config == ContainerConfig(**data_expected)


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
def test_propagate_container_config_bids(
    valid_config_data, data_root, data_pipeline, data_expected
):
    pipeline_name = "bids_converter"
    pipeline_version = "1.0"
    step_name = "step1"
    data = valid_config_data
    data["CONTAINER_CONFIG"] = data_root
    data["BIDS_PIPELINES"] = [
        {
            "NAME": pipeline_name,
            "VERSION": pipeline_version,
            "STEP": step_name,
            "CONTAINER_CONFIG": data_pipeline,
        }
    ]

    container_config = (
        Config(**data)
        .get_bids_pipeline_config(pipeline_name, pipeline_version, step_name)
        .get_container_config()
    )

    assert container_config == ContainerConfig(**data_expected)


@pytest.mark.parametrize(
    "pipeline,version",
    [("pipeline1", "v1"), ("pipeline2", "2.0")],
)
def test_get_pipeline_config(pipeline, version, valid_config_data):
    assert isinstance(
        Config(**valid_config_data).get_pipeline_config(pipeline, version),
        PipelineConfig,
    )


def test_get_pipeline_config_missing(valid_config_data):
    with pytest.raises(ValueError):
        Config(**valid_config_data).get_pipeline_config("not_a_pipeline", "v1")


@pytest.mark.parametrize(
    "pipeline,version,step",
    [("bids_converter", "1.0", "step1"), ("bids_converter", "1.0", "step2")],
)
def test_get_bids_pipeline_config(pipeline, version, step, valid_config_data):
    assert isinstance(
        Config(**valid_config_data).get_bids_pipeline_config(pipeline, version, step),
        PipelineConfig,
    )


def test_get_bids_pipeline_config_missing(valid_config_data):
    with pytest.raises(ValueError):
        Config(**valid_config_data).get_bids_pipeline_config(
            "not_a_bids_pipeline", "v1", "step1"
        )


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
        Config.load(DPATH_TEST_DATA / "config_invalid1.json")


def test_globals(valid_config_data, tmp_path: Path):
    pattern_to_replace1 = "[[FREESURFER_LICENSE_FILE]]"
    replacement_value1 = "/path/to/license.txt"
    pattern_to_replace2 = "[[TEMPLATEFLOW_HOME]]"
    replacement_value2 = "/path/to/templateflow"

    valid_config_data["GLOBALS"] = {
        pattern_to_replace1: replacement_value1,
        pattern_to_replace2: replacement_value2,
    }
    valid_config_data["PROC_PIPELINES"] = [
        {
            "NAME": "fmriprep",
            "VERSION": "23.1.3",
            "INVOCATION": {
                "fs_license_file": pattern_to_replace1,
            },
            "CONTAINER_CONFIG": {
                "ARGS": ["--bind", pattern_to_replace1, "--bind", pattern_to_replace2],
                "ENV_VARS": {"TEMPLATEFLOW_HOME": pattern_to_replace2},
            },
        },
    ]

    fpath = tmp_path / "config.json"
    Config(**valid_config_data).save(fpath)
    config_to_check = Config.load(fpath, apply_globals_replacement=True)
    assert config_to_check.PROC_PIPELINES[0] == PipelineConfig(
        **{
            "NAME": "fmriprep",
            "VERSION": "23.1.3",
            "INVOCATION": {
                "fs_license_file": replacement_value1,
            },
            "CONTAINER_CONFIG": {
                "ARGS": ["--bind", replacement_value1, "--bind", replacement_value2],
                "ENV_VARS": {"TEMPLATEFLOW_HOME": replacement_value2},
            },
        },
    )
