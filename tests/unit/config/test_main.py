"""Tests for the config module."""

import json
from contextlib import nullcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from nipoppy.config.container import ContainerConfig
from nipoppy.config.main import Config, PipelineVariables
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import CURRENT_SCHEMA_VERSION, PipelineTypeEnum
from nipoppy.exceptions import ConfigError
from nipoppy.utils.utils import FPATH_SAMPLE_CONFIG
from tests.conftest import DPATH_TEST_DATA

FIELDS_PIPELINE_VARIABLES = ["BIDSIFICATION", "PROCESSING", "EXTRACTION"]
REQUIRED_FIELDS_CONFIG = []
FIELDS_CONFIG = REQUIRED_FIELDS_CONFIG + [
    "SUBSTITUTIONS",
    "CUSTOM",
    "CONTAINER_CONFIG",
    "DICOM_DIR_MAP_FILE",
    "DICOM_DIR_PARTICIPANT_FIRST",
    "HPC_PREAMBLE",
    "PIPELINE_VARIABLES",
]


@pytest.fixture(scope="function")
def valid_config_data():
    return {}


@pytest.fixture(scope="function")
def pipeline_variables():
    data = {
        "BIDSIFICATION": {
            "bids_pipeline": {
                "0.0.1": {
                    "bids1": "val1",
                    "bids2": "val2",
                },
            },
        },
        "PROCESSING": {
            "proc_pipeline": {
                "0.1.0": {
                    "proc1": "val1",
                },
                "0.2.0": {
                    "proc1": "val1",
                    "proc2": "val2",
                },
            },
        },
        "EXTRACTION": {
            "extraction_pipeline": {
                "1.0.0": {},
            },
        },
    }
    return PipelineVariables(**data)


def test_fields(valid_config_data: dict):
    config = Config(
        **{k: v for (k, v) in valid_config_data.items() if k in REQUIRED_FIELDS_CONFIG}
    )
    for field in FIELDS_CONFIG:
        assert hasattr(config, field)
    assert len(config.model_dump()) == len(FIELDS_CONFIG)


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
    "hpc_preamble", ["module load preamble", ["module load preamble"]]
)
def test_hpc_preamble_list(hpc_preamble, valid_config_data):
    valid_config_data["HPC_PREAMBLE"] = hpc_preamble
    config = Config(**valid_config_data)
    assert config.HPC_PREAMBLE == ["module load preamble"]


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
    "substitutions", [{"": "abc"}, {"valid_key": "abc", "": "def"}]
)
def test_check_substitutions_empty_key(valid_config_data, substitutions):
    with pytest.raises(ValueError, match="Substitutions cannot have empty keys"):
        Config(**valid_config_data, SUBSTITUTIONS=substitutions)


def test_check_substitutions_strip_values(valid_config_data):
    substitutions_before = {
        "key1": "  value1",
        "key2": "value2  ",
        "key3": "  value3  ",
        "key4": "value4",
    }
    substitutions_after = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3",
        "key4": "value4",
    }
    with pytest.warns(
        UserWarning,
        match=r"Substitution value for key '.*' has leading/trailing whitespace: '.*'.",
    ):
        config = Config(**valid_config_data, SUBSTITUTIONS=substitutions_before)
    assert config.SUBSTITUTIONS == substitutions_after


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
            "SCHEMA_VERSION": CURRENT_SCHEMA_VERSION,
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
        DPATH_TEST_DATA / "config_invalid1.json",  # has PROC_PIPELINES (old)
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


@pytest.mark.parametrize(
    "pipeline_type,pipeline_name,pipeline_version,json_obj,expected",
    [
        (
            PipelineTypeEnum.BIDSIFICATION,
            "bids_pipeline",
            "0.0.1",
            {"some_key": "123_[[bids1]]"},
            {"some_key": "123_val1"},
        ),
        (
            PipelineTypeEnum.PROCESSING,
            "proc_pipeline",
            "0.2.0",
            {"[[proc1]]_key": "123_[[bids1]]"},
            {"val1_key": "123_[[bids1]]"},
        ),
        (
            PipelineTypeEnum.EXTRACTION,
            "extraction_pipeline",
            "1.0.0",
            {"some_key": "123_[[bids1]]"},
            {"some_key": "123_[[bids1]]"},
        ),
    ],
)
def test_apply_pipeline_variables(
    valid_config_data,
    pipeline_variables,
    pipeline_type,
    pipeline_name,
    pipeline_version,
    json_obj,
    expected,
):
    config = Config(**valid_config_data)
    config.PIPELINE_VARIABLES = pipeline_variables
    assert (
        config.apply_pipeline_variables(
            pipeline_type, pipeline_name, pipeline_version, json_obj
        )
        == expected
    )


def test_pipeline_variables(valid_config_data: dict):
    config = Config(
        **{k: v for (k, v) in valid_config_data.items() if k in REQUIRED_FIELDS_CONFIG}
    )
    pipeline_vars = config.PIPELINE_VARIABLES
    for field in FIELDS_PIPELINE_VARIABLES:
        assert hasattr(pipeline_vars, field)


def test_pipeline_variables_not_extra_fields():
    with pytest.raises(ValidationError):
        PipelineVariables(NOT_A_FIELD="x")


@pytest.mark.parametrize(
    "pipeline_type,pipeline_name,pipeline_version,expected",
    [
        (
            PipelineTypeEnum.BIDSIFICATION,
            "bids_pipeline",
            "0.0.1",
            {"bids1": "val1", "bids2": "val2"},
        ),
        (PipelineTypeEnum.PROCESSING, "proc_pipeline", "0.1.0", {"proc1": "val1"}),
        (
            PipelineTypeEnum.PROCESSING,
            "proc_pipeline",
            "0.2.0",
            {"proc1": "val1", "proc2": "val2"},
        ),
        (PipelineTypeEnum.EXTRACTION, "extraction_pipelines", "1.0.0", {}),
    ],
)
def test_pipeline_variables_get_variables(
    pipeline_variables: PipelineVariables,
    pipeline_type,
    pipeline_name,
    pipeline_version,
    expected,
):
    assert (
        pipeline_variables.get_variables(pipeline_type, pipeline_name, pipeline_version)
        == expected
    )


def test_pipeline_variables_get_variables_error_pipeline_type(
    pipeline_variables: PipelineVariables,
):
    with pytest.raises(ConfigError, match="Invalid pipeline type"):
        pipeline_variables.get_variables("INVALID", "pipeline1", "version1")


def test_pipeline_variables_get_variables_unknown(
    pipeline_variables: PipelineVariables,
):
    assert (
        pipeline_variables.get_variables(PipelineTypeEnum.PROCESSING, "xyz", "123")
        == {}
    )


@pytest.mark.parametrize(
    "pipeline_type,pipeline_name,pipeline_version,to_set",
    [
        (
            PipelineTypeEnum.BIDSIFICATION,
            "new_bids_pipeline",
            "1.1.1",
            {"var1": "val1", "var2": "val2"},
        ),
        (PipelineTypeEnum.PROCESSING, "proc_pipeline", "0.1.0", {}),
        (PipelineTypeEnum.EXTRACTION, "extraction_pipelines", "1.0.0", {"A": "1"}),
    ],
)
def test_pipeline_variables_set_variables(
    pipeline_variables: PipelineVariables,
    pipeline_type,
    pipeline_name,
    pipeline_version,
    to_set,
):
    pipeline_variables.set_variables(
        pipeline_type, pipeline_name, pipeline_version, to_set
    )
    assert (
        pipeline_variables.get_variables(pipeline_type, pipeline_name, pipeline_version)
        == to_set
    )


def test_pipeline_variables_set_variables_error_pipeline_type(
    pipeline_variables: PipelineVariables,
):
    with pytest.raises(ConfigError, match="Invalid pipeline type"):
        pipeline_variables.set_variables("INVALID", "pipeline1", "version1", {})


def test_pipeline_variables_validation(pipeline_variables: PipelineVariables):
    # test the conversion to defaultdict
    # any unknown pipeline should have an empty dict
    assert pipeline_variables.BIDSIFICATION["unknown_pipeline"]["v1"] == {}
    assert pipeline_variables.PROCESSING["unknown_pipeline2"]["v2"] == {}
    assert pipeline_variables.EXTRACTION["unknown_pipeline3"]["v3"] == {}
