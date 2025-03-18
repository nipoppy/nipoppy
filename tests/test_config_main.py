"""Tests for the config module."""

import json
from contextlib import nullcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from nipoppy.config.container import ContainerConfig
from nipoppy.config.main import Config
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.utils import FPATH_SAMPLE_CONFIG

from .conftest import DPATH_TEST_DATA

REQUIRED_FIELDS_CONFIG = []
FIELDS_CONFIG = REQUIRED_FIELDS_CONFIG + [
    "SUBSTITUTIONS",
    "CUSTOM",
    "CONTAINER_CONFIG",
    "DICOM_DIR_MAP_FILE",
    "DICOM_DIR_PARTICIPANT_FIRST",
]


@pytest.fixture(scope="function")
def valid_config_data():
    return {}


def test_fields(valid_config_data: dict):
    config = Config(
        **{k: v for (k, v) in valid_config_data.items() if k in REQUIRED_FIELDS_CONFIG}
    )
    for field in FIELDS_CONFIG:
        assert hasattr(config, field)
    assert len(config.model_fields) == len(FIELDS_CONFIG)


def test_no_extra_fields(valid_config_data):
    with pytest.raises(ValidationError):
        Config(**valid_config_data, NOT_A_FIELD="x")


@pytest.mark.parametrize(
    "deprecated_field", ["DATASET_NAME", "VISIT_IDS", "SESSION_IDS"]
)
def test_deprecated_fields(deprecated_field, valid_config_data):
    with pytest.warns(DeprecationWarning):
        Config(**valid_config_data, **{deprecated_field: "x"})


@pytest.mark.parametrize(
    "dicom_dir_map_file,dicom_dir_participant_first,is_valid",
    [
        (None, None, True),
        ("path", None, True),
        (None, True, True),
        (None, False, True),
        ("path", True, False),
    ],
)
def test_check_dicom_dir_options(
    valid_config_data, dicom_dir_map_file, dicom_dir_participant_first, is_valid
):
    valid_config_data["DICOM_DIR_MAP_FILE"] = dicom_dir_map_file
    valid_config_data["DICOM_DIR_PARTICIPANT_FIRST"] = dicom_dir_participant_first
    with (
        pytest.raises(ValueError, match="Cannot specify both")
        if not is_valid
        else nullcontext()
    ):
        assert isinstance(Config(**valid_config_data), Config)


@pytest.mark.parametrize(
    "data_root,data_pipeline,data_step,data_expected",
    [
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"]},
            {"ARGS": ["--no-home"]},
            {"ARGS": ["--no-home", "--fakeroot", "--cleanenv"]},
        ),
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"], "INHERIT": "false"},
            {},
            {"ARGS": ["--fakeroot"], "INHERIT": "true"},
        ),
        (
            {"ARGS": ["--cleanenv"]},
            {"ARGS": ["--fakeroot"]},
            {"ARGS": ["--no-home"], "INHERIT": "false"},
            {"ARGS": ["--no-home"], "INHERIT": "false"},
        ),
        (
            {"ARGS": ["--cleanenv"]},
            {},
            {"ARGS": ["--bind", "[[HEUDICONV_HEURISTIC_FILE]]"]},
            {"ARGS": ["--bind", "[[HEUDICONV_HEURISTIC_FILE]]", "--cleanenv"]},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {"ENV_VARS": {"VAR2": "2"}},
            {},
            {"ENV_VARS": {"VAR1": "1", "VAR2": "2"}},
        ),
        (
            {"ENV_VARS": {"VAR1": "1"}},
            {},
            {"ENV_VARS": {"VAR2": "2"}, "INHERIT": "false"},
            {"ENV_VARS": {"VAR2": "2"}, "INHERIT": "false"},
        ),
    ],
)
def test_propagate_container_config(
    valid_config_data,
    data_root,
    data_pipeline,
    data_step,
    data_expected,
):
    pipeline_name = "pipeline1"
    pipeline_version = "1.0"
    step_name = "step1"
    data = valid_config_data
    container_config_key = "CONTAINER_CONFIG"
    data[container_config_key] = data_root
    pipeline_config = BasePipelineConfig(
        **{
            "NAME": pipeline_name,
            "VERSION": pipeline_version,
            container_config_key: data_pipeline,
            "STEPS": [{"NAME": step_name, container_config_key: data_step}],
        }
    )

    Config(**data).propagate_container_config_to_pipeline(pipeline_config)
    container_config = pipeline_config.get_step_config(step_name).get_container_config()

    assert container_config == ContainerConfig(**data_expected)


def test_save(tmp_path: Path, valid_config_data):
    fpath_out = tmp_path / "config.json"
    config = Config(**valid_config_data)
    config.save(fpath_out)
    assert fpath_out.exists()
    with fpath_out.open("r") as file:
        assert isinstance(json.load(file), dict)


@pytest.mark.parametrize(
    "substitutions,json_obj,expected",
    [
        (
            {"VALUE1": "AAA", "VALUE2": "BBB"},
            {"KEY": "VALUE1 VALUE2"},
            {"KEY": "AAA BBB"},
        ),
        (
            {"VALUE1": "CCC", "VALUE2": "DDD"},
            ["AAA BBB VALUE1", "VALUE2"],
            ["AAA BBB CCC", "DDD"],
        ),
    ],
)
def test_apply_substitutions(valid_config_data, substitutions, json_obj, expected):
    config = Config(**valid_config_data, SUBSTITUTIONS=substitutions)
    assert config.apply_substitutions_to_json(json_obj) == expected


@pytest.mark.parametrize(
    "path",
    [
        FPATH_SAMPLE_CONFIG,
        DPATH_TEST_DATA / "config1.json",
        DPATH_TEST_DATA / "config2.json",
        DPATH_TEST_DATA / "config3.json",
    ],
)
def test_load(path):
    config = Config.load(path)
    assert isinstance(config, Config)
    for field in REQUIRED_FIELDS_CONFIG:
        assert hasattr(config, field)


@pytest.mark.parametrize(
    "path",
    [
        DPATH_TEST_DATA / "config_invalid2.json",  # has PROC_PIPELINES (old)
    ],
)
def test_load_invalid(path):
    with pytest.raises(ValueError):
        Config.load(path)


def test_load_apply_substitutions(valid_config_data, tmp_path: Path):
    pattern_to_replace1 = "[[FREESURFER_LICENSE_FILE]]"
    replacement_value1 = "/path/to/license.txt"
    pattern_to_replace2 = "[[TEMPLATEFLOW_HOME]]"
    replacement_value2 = "/path/to/templateflow"

    substitutions = {
        pattern_to_replace1: replacement_value1,
        pattern_to_replace2: replacement_value2,
    }
    valid_config_data["SUBSTITUTIONS"] = substitutions

    fpath = tmp_path / "config.json"
    Config(**valid_config_data).save(fpath)
    config_to_check = Config.load(fpath, apply_substitutions=True)

    # also check that the SUBSTITUTIONS field remains the same
    assert config_to_check.SUBSTITUTIONS == substitutions


@pytest.mark.parametrize(
    "apply_substitutions,substitutions",
    [
        (False, {"[[PATTERN1]]": "replacement1", "[[PATTERN2]]": "replacement2"}),
        (True, {}),
    ],
)
def test_load_no_substitutions(
    valid_config_data, tmp_path: Path, apply_substitutions, substitutions
):
    valid_config_data["SUBSTITUTIONS"] = substitutions

    fpath = tmp_path / "config.json"
    config_expected = Config(**valid_config_data)
    config_expected.save(fpath)

    # check that the loaded config is the same
    assert (
        Config.load(fpath, apply_substitutions=apply_substitutions) == config_expected
    )
