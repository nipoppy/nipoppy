"""Tests for BidsConversionWorkflow."""

from pathlib import Path

import pytest

from nipoppy.config.main import Config
from nipoppy.config.pipeline import PipelineConfig
from nipoppy.workflows.bids_conversion import BidsConversionRunner

from .conftest import create_empty_dataset, get_config


@pytest.fixture
def config() -> Config:
    return get_config(
        bids_pipelines=[
            {"NAME": "heudiconv", "VERSION": "0.12.2", "STEP": "prepare"},
            {"NAME": "heudiconv", "VERSION": "0.12.2", "STEP": "convert"},
            {"NAME": "dcm2bids", "VERSION": "3.1.0", "STEP": "prepare"},
            {"NAME": "dcm2bids", "VERSION": "3.1.0", "STEP": "convert"},
        ]
    )


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step",
    [
        ("heudiconv", "0.12.2", "prepare"),
        ("heudiconv", "0.12.2", "convert"),
        ("dcm2bids", "3.1.0", "prepare"),
        ("dcm2bids", "3.1.0", "convert"),
    ],
)
def test_builtin_pipelines(
    pipeline_name, pipeline_version, pipeline_step, config: Config, tmp_path: Path
):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        pipeline_step=pipeline_step,
    )

    config.save(workflow.layout.fpath_config)

    assert isinstance(workflow.pipeline_config, PipelineConfig)
    assert isinstance(workflow.descriptor, dict)


def test_setup(config: Config, tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    create_empty_dataset(workflow.dpath_root)
    config.save(workflow.layout.fpath_config)
    workflow.run_setup()
    assert not workflow.dpath_pipeline.exists()
