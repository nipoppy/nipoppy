"""Tests for the pipeline configuration class."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from nipoppy.config.pipeline import (
    BasePipelineConfig,
    BidsPipelineConfig,
    ProcPipelineConfig,
)
from nipoppy.config.pipeline_step import ProcPipelineStepConfig

FIELDS_PIPELINE_BASE = [
    "NAME",
    "VERSION",
    "DESCRIPTION",
    "CONTAINER_INFO",
    "CONTAINER_CONFIG",
    "STEPS",
]


@pytest.fixture(scope="function")
def valid_data() -> dict:
    return {
        "NAME": "my_pipeline",
        "VERSION": "1.0.0",
    }


@pytest.mark.parametrize(
    "pipeline_config_class,fields,additional_data_list",
    [
        (
            BasePipelineConfig,
            FIELDS_PIPELINE_BASE,
            [
                {},
                {"DESCRIPTION": "My pipeline"},
                {"CONTAINER_CONFIG": {"ARGS": ["--cleanenv"]}},
                {"STEPS": []},
            ],
        ),
    ],
)
def test_fields(pipeline_config_class, fields, valid_data, additional_data_list):
    for additional_data in additional_data_list:
        pipeline_config: BasePipelineConfig = pipeline_config_class(
            **valid_data, **additional_data
        )
        for field in fields:
            assert hasattr(pipeline_config, field)

    assert len(set(pipeline_config.model_fields.keys())) == len(fields)


@pytest.mark.parametrize(
    "data",
    [{}, {"NAME": "my_pipeline"}, {"VERSION": "1.0.0"}],
)
def test_fields_missing_required(data):
    with pytest.raises(ValidationError):
        BasePipelineConfig(**data)


@pytest.mark.parametrize(
    "pipeline_config_class", [ProcPipelineConfig, BidsPipelineConfig]
)
def test_fields_no_extra(pipeline_config_class, valid_data):
    with pytest.raises(ValidationError):
        pipeline_config_class(**valid_data, not_a_field="a")


def test_step_names_error_duplicate(valid_data):
    with pytest.raises(ValidationError, match="Found at least two steps with NAME"):
        BasePipelineConfig(
            **valid_data,
            STEPS=[
                {"NAME": "step1"},
                {"NAME": "step1"},
            ],
        )


def test_substitutions():
    data = {
        "NAME": "my_pipeline",
        "VERSION": "1.0.0",
        "DESCRIPTION": "[[PIPELINE_NAME]] version [[PIPELINE_VERSION]]",
        "STEPS": [
            {
                "NAME": "step1",
                "INVOCATION_FILE": "[[PIPELINE_NAME]]-[[PIPELINE_VERSION]].json",
            }
        ],
    }
    pipeline_config = ProcPipelineConfig(**data)
    assert pipeline_config.DESCRIPTION == "my_pipeline version 1.0.0"
    assert str(pipeline_config.STEPS[0].INVOCATION_FILE) == "my_pipeline-1.0.0.json"


@pytest.mark.parametrize("container", ["my_container.sif", "my_other_container.sif"])
def test_get_fpath_container(valid_data, container):
    pipeline_config = BasePipelineConfig(
        **valid_data, CONTAINER_INFO={"FILE": container}
    )
    assert pipeline_config.get_fpath_container() == Path(container)


@pytest.mark.parametrize(
    "step_name,expected_name",
    [
        ("step1", "step1"),
        ("step2", "step2"),
        (None, "step1"),
    ],
)
def test_get_step_config(valid_data, step_name, expected_name):
    pipeling_config = BasePipelineConfig(
        **valid_data,
        STEPS=[
            ProcPipelineStepConfig(NAME="step1", INVOCATION_FILE="step1.json"),
            ProcPipelineStepConfig(NAME="step2", INVOCATION_FILE="step2.json"),
        ],
    )

    assert pipeling_config.get_step_config(step_name).NAME == expected_name


def test_get_step_config_no_steps(valid_data):
    pipeline_config = BasePipelineConfig(**valid_data, STEPS=[])
    with pytest.raises(ValueError, match="No steps specified for pipeline"):
        pipeline_config.get_step_config()


def test_get_step_config_invalid(valid_data):
    pipeline_config = BasePipelineConfig(
        **valid_data,
        STEPS=[
            ProcPipelineStepConfig(NAME="step1", INVOCATION_FILE="step1.json"),
            ProcPipelineStepConfig(NAME="step2", INVOCATION_FILE="step2.json"),
        ],
    )
    with pytest.raises(ValueError, match="not found in pipeline"):
        pipeline_config.get_step_config("invalid_step")
