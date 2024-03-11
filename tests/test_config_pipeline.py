"""Tests for the pipeline configuration class."""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from nipoppy.config.pipeline import PipelineConfig

FIELDS_PIPELINE = [
    "CONTAINER",
    "URI",
    "SINGULARITY_CONFIG",
    "DESCRIPTOR",
    "INVOCATION",
    "PYBIDS_IGNORE",
]


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
