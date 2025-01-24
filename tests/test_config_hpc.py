"""Tests for the HpcConfig class."""

import pytest
from pydantic import ValidationError

from nipoppy.config.hpc import HpcConfig


@pytest.mark.parametrize(
    "data", [{"random_field1": "abc"}, {"random_field2": 123}, {"xxxx": ""}]
)
def test_custom_fields_allowed(data):
    assert HpcConfig(**data)


@pytest.mark.parametrize("data", [{"field1": 123}, {"field2": True}])
def test_str_values(data):
    config = HpcConfig(**data)
    for value in config.model_dump().values():
        assert isinstance(value, str), f"Value should be string, got {type(value)}"


def test_none_value():
    config = HpcConfig(field1=None)
    assert getattr(config, "field1") is None


@pytest.mark.parametrize(
    "data",
    [
        {"job_name": "abc"},
        {"dataset_root": "123"},
        {"command": "echo hello"},
        {"queue": "slurm"},
    ],
)
def test_reserved_keywords_error(data):
    with pytest.raises(ValidationError, match="Reserved key .* found"):
        HpcConfig(**data)
