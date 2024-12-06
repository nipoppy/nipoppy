"""Tests for the pipeline configuration class."""

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from nipoppy.config.pipeline import (
    BasePipelineConfig,
    BidsPipelineConfig,
    ExtractionPipelineConfig,
    PipelineInfo,
    ProcPipelineConfig,
)
from nipoppy.config.pipeline_step import BasePipelineStepConfig

FIELDS_BASE_PIPELINE = [
    "NAME",
    "VERSION",
    "DESCRIPTION",
    "CONTAINER_INFO",
    "CONTAINER_CONFIG",
    "STEPS",
]
FIELDS_BIDS_PIPELINE = FIELDS_BASE_PIPELINE
FIELDS_PROC_PIPELINE = FIELDS_BASE_PIPELINE + ["TRACKER_CONFIG_FILE"]
FIELDS_EXTRACTION_PIPELINE = FIELDS_BASE_PIPELINE + ["PROC_DEPENDENCIES"]
FIELDS_PIPELINE_INFO = ["NAME", "VERSION", "STEP"]


@pytest.fixture(scope="function")
def valid_data() -> dict:
    return {
        "NAME": "my_pipeline",
        "VERSION": "1.0.0",
    }


@pytest.mark.parametrize(
    "model_class,fields",
    [
        (BasePipelineConfig, FIELDS_BASE_PIPELINE),
        (BidsPipelineConfig, FIELDS_BIDS_PIPELINE),
        (ProcPipelineConfig, FIELDS_PROC_PIPELINE),
        (PipelineInfo, FIELDS_PIPELINE_INFO),
    ],
)
def test_fields(model_class, fields, valid_data):
    config: BaseModel = model_class(**valid_data)
    for field in fields:
        assert hasattr(config, field)

    assert len(set(config.model_fields.keys())) == len(fields)


def test_fields_extraction_pipeline(valid_data):
    config = ExtractionPipelineConfig(
        **valid_data,
        PROC_DEPENDENCIES=[valid_data],
    )
    for field in FIELDS_EXTRACTION_PIPELINE:
        assert hasattr(config, field)
    assert len(set(config.model_fields.keys())) == len(FIELDS_EXTRACTION_PIPELINE)


@pytest.mark.parametrize("model_class", [BasePipelineConfig, PipelineInfo])
@pytest.mark.parametrize(
    "data",
    [{}, {"NAME": "my_pipeline"}, {"VERSION": "1.0.0"}],
)
def test_fields_missing_required(model_class, data):
    with pytest.raises(ValidationError):
        model_class(**data)


@pytest.mark.parametrize(
    "model_class",
    [ProcPipelineConfig, BidsPipelineConfig, ExtractionPipelineConfig, PipelineInfo],
)
def test_fields_no_extra(model_class, valid_data):
    with pytest.raises(ValidationError):
        model_class(**valid_data, not_a_field="a")


def test_step_names_error_duplicate(valid_data):
    with pytest.raises(ValidationError, match="Found at least two steps with NAME"):
        BasePipelineConfig(
            **valid_data,
            STEPS=[
                {"NAME": "step1"},
                {"NAME": "step1"},
            ],
        )


def test_error_no_dependencies():
    with pytest.raises(ValidationError, match="PROC_DEPENDENCIES is an empty list"):
        ExtractionPipelineConfig(
            NAME="my_pipeline",
            VERSION="1.0.0",
            PROC_DEPENDENCIES=[],
        )


def test_warning_if_duplicate_dependencies():
    with pytest.warns(
        UserWarning,
        match="PROC_DEPENDENCIES contains duplicate entries for extraction pipeline",
    ):
        ExtractionPipelineConfig(
            NAME="my_pipeline",
            VERSION="1.0.0",
            PROC_DEPENDENCIES=[
                PipelineInfo(NAME="my_pipeline", VERSION="1.0.0", STEP="step1"),
                PipelineInfo(NAME="my_pipeline", VERSION="1.0.0", STEP="step1"),
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
                "INVOCATION_FILE": "[[PIPELINE_NAME]]-[[PIPELINE_VERSION]]/invocation.json",  # noqa: E501
            }
        ],
    }
    pipeline_config = BasePipelineConfig(**data)
    assert pipeline_config.DESCRIPTION == "my_pipeline version 1.0.0"
    assert (
        str(pipeline_config.STEPS[0].INVOCATION_FILE)
        == "my_pipeline-1.0.0/invocation.json"
    )


@pytest.mark.parametrize("container", ["my_container.sif", "my_other_container.sif"])
def test_get_fpath_container(valid_data, container):
    pipeline_config = BasePipelineConfig(
        **valid_data, CONTAINER_INFO={"FILE": container}
    )
    assert pipeline_config.get_fpath_container() == Path(container)


@pytest.mark.parametrize(
    "step_name,expected_name",
    [("step1", "step1"), ("step2", "step2"), (None, "step1")],
)
def test_get_step_config(valid_data, step_name, expected_name):
    pipeling_config = BasePipelineConfig(
        **valid_data,
        STEPS=[
            BasePipelineStepConfig(NAME="step1", INVOCATION_FILE="step1.json"),
            BasePipelineStepConfig(NAME="step2", INVOCATION_FILE="step2.json"),
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
            BasePipelineStepConfig(NAME="step1", INVOCATION_FILE="step1.json"),
            BasePipelineStepConfig(NAME="step2", INVOCATION_FILE="step2.json"),
        ],
    )
    with pytest.raises(ValueError, match="not found in pipeline"):
        pipeline_config.get_step_config("invalid_step")
