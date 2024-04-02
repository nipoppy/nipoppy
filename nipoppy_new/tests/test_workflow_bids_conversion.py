"""Tests for BidsConversionWorkflow."""

from pathlib import Path

import pytest

from nipoppy.config.base import Config
from nipoppy.config.pipeline import PipelineConfig
from nipoppy.workflows.bids_conversion import BidsConversionRunner


@pytest.fixture
def config() -> Config:
    return Config(
        DATASET_NAME="my_dataset",
        SESSIONS=[],
        VISITS=[],
        BIDS={
            "heudiconv": {"0.12.2": {"prepare": {}, "convert": {}}},
            "dcm2bids": {"3.1.0": {"prepare": {}, "convert": {}}},
        },
        PROC_PIPELINES={},
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
    config.save(workflow.layout.fpath_config)
    workflow.run_setup()
    assert not workflow.dpath_pipeline.exists()
