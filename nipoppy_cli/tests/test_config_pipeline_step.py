"""Tests for the pipeline step configuration class."""

import re

import pytest
from pydantic import ValidationError

from nipoppy.config.pipeline import PipelineStepConfig

FIELDS_STEP = [
    "NAME",
    "DESCRIPTOR_FILE",
    "INVOCATION_FILE",
    "PYBIDS_IGNORE",
    "CONTAINER_CONFIG",
]


@pytest.mark.parametrize(
    "data",
    [
        {"NAME": "step_name"},
        {"DESCRIPTOR_FILE": "PATH_TO_DESCRIPTOR_FILE"},
        {"INVOCATION_FILE": "PATH_TO_INVOCATION_FILE"},
        {"PYBIDS_IGNORE": ["ignore1", "ignore2"]},
        {"CONTAINER_CONFIG": {}},
    ],
)
def test_field(data):
    pipeline_step_config = PipelineStepConfig(**data)
    for field in FIELDS_STEP:
        assert hasattr(pipeline_step_config, field)

    assert len(set(pipeline_step_config.model_fields.keys())) == len(FIELDS_STEP)


def test_no_extra_field():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PipelineStepConfig(not_a_field="a")


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
    step_config = PipelineStepConfig(PYBIDS_IGNORE=orig_patterns)
    step_config.add_pybids_ignore_patterns(new_patterns)
    assert step_config.PYBIDS_IGNORE == expected
