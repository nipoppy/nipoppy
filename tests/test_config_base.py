"""Tests for the config module."""

import json
import re
from pathlib import Path

import pytest
from conftest import DPATH_TEST_DATA
from pydantic import ValidationError

from nipoppy.config.base import Config, PipelineConfig, load_config
from nipoppy.config.singularity import SingularityConfig
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
        {"CONTAINER": "/my/container"},
        {"URI": "docker://container"},
        {"SINGULARITY_CONFIG": {"ARGS": ["--cleanenv"]}},
        {"DESCRIPTOR": {}},
        {"INVOCATION": {"arg1": "val1", "arg2": "val2"}},
        {"PYBIDS_IGNORE": ["ignore1", "ignore2"]},
        {"DESCRIPTION": "My pipeline"},
    ],
)
def test_pipeline_config(data):
    for field in FIELDS_PIPELINE:
        assert hasattr(PipelineConfig(**data), field)


@pytest.mark.parametrize("container", ["my_container.sif", "my_other_container.sif"])
def test_get_container(container):
    pipeline_config = PipelineConfig(CONTAINER=container)
    assert pipeline_config.get_container() == Path(container)


def test_get_container_error():
    pipeline_config = PipelineConfig()
    with pytest.raises(RuntimeError, match="No container specified for the pipeline"):
        pipeline_config.get_container()


@pytest.mark.parametrize(
    "orig_patterns,new_patterns,expected",
    [
        ([], [], []),
        (["a"], "b", [re.compile("a"), re.compile("b")]),
        (["a"], ["b"], [re.compile("a"), re.compile("b")]),
        (["a"], ["b", "c"], [re.compile("a"), re.compile("b"), re.compile("c")]),
        (["a"], "a", [re.compile("a")]),
        ([re.compile("a")], ["b"], [re.compile("a"), re.compile("b")]),
    ],
)
def test_add_pybids_ignore_patterns(orig_patterns, new_patterns, expected):
    pipeline_config = PipelineConfig(PYBIDS_IGNORE=orig_patterns)
    pipeline_config.add_pybids_ignore_patterns(new_patterns)
    assert pipeline_config.PYBIDS_IGNORE == expected


def test_pipeline_config_no_extra_fields():
    with pytest.raises(ValidationError):
        PipelineConfig(not_a_field="a")


@pytest.mark.parametrize("field_name", ["not_a_field", "also_not_a_field"])
def test_config_extra_fields_allowed(field_name, valid_config_data):
    args = valid_config_data
    args[field_name] = "extra"
    assert hasattr(Config(**args), field_name)


def test_config_check_no_duplicate_pipeline(valid_config_data):
    data = valid_config_data
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
@pytest.mark.parametrize("pipeline_type", ["BIDS", "PROC_PIPELINES"])
def test_config_propagate_singularity_config(
    data_root, data_pipeline, data_expected, pipeline_type
):
    pipeline_name = "pipeline1"
    pipeline_version = "1.0"
    data = {
        "DATASET_NAME": "my_dataset",
        "SESSIONS": [],
        "SINGULARITY_CONFIG": data_root,
        "BIDS": {},
        "PROC_PIPELINES": {},
    }
    data.update(
        {
            pipeline_type: {
                pipeline_name: {pipeline_version: {"SINGULARITY_CONFIG": data_pipeline}}
            }
        }
    )
    print(f"data: {data}")
    singularity_config = getattr(Config(**data), pipeline_type)[pipeline_name][
        pipeline_version
    ].get_singularity_config()
    assert singularity_config == SingularityConfig(**data_expected)


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
