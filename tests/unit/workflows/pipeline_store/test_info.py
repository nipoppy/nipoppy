"""Tests for PipelineInfoWorkflow."""

from pathlib import Path

import pytest

from nipoppy.env import PipelineTypeEnum
from nipoppy.exceptions import WorkflowError
from nipoppy.layout import DatasetLayout
from nipoppy.workflows.pipeline_store.info import PipelineInfoWorkflow
from tests.conftest import create_empty_dataset, create_pipeline_config_files


def _pipeline_config(version: str) -> dict:
    return {
        "NAME": "example",
        "VERSION": version,
        "DESCRIPTION": "An example processing pipeline",
        "STEPS": [
            {
                "NAME": "preprocess",
                "ANALYSIS_LEVEL": "participant",
                "DESCRIPTOR_FILE": "descriptor.json",
                "INVOCATION_FILE": "invocation.json",
                "TRACKER_CONFIG_FILE": "tracker.json",
            }
        ],
    }


@pytest.fixture()
def dpath_root(tmp_path: Path) -> Path:
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)
    create_pipeline_config_files(
        DatasetLayout(dpath_root).dpath_pipelines,
        processing_pipelines=[
            _pipeline_config("1.0.0"),
            _pipeline_config("2.0.0"),
        ],
    )
    return dpath_root


@pytest.mark.no_xdist
def test_run_main_uses_latest_version(
    dpath_root: Path,
    caplog: pytest.LogCaptureFixture,
):
    workflow = PipelineInfoWorkflow(dpath_root, pipeline_name="example")

    workflow.run_main()

    output = "\n".join(record.message for record in caplog.records)
    expected_bundle = (
        workflow.study.layout.dpath_pipelines
        / DatasetLayout.pipeline_type_to_dname_map[PipelineTypeEnum.PROCESSING]
        / "example-2.0.0"
    )
    assert "example 2.0.0" in output
    assert f"Bundle: {expected_bundle}" in output
    assert "Type: processing" in output
    assert "Description: An example processing pipeline" in output
    assert "Steps: 1" in output
    assert "Step 1: preprocess" in output
    assert "Analysis level: participant" in output
    assert f"Descriptor: {expected_bundle / 'descriptor.json'}" in output
    assert f"Invocation: {expected_bundle / 'invocation.json'}" in output
    assert f"Tracker config: {expected_bundle / 'tracker.json'}" in output


@pytest.mark.no_xdist
def test_run_main_uses_requested_version(
    dpath_root: Path,
    caplog: pytest.LogCaptureFixture,
):
    workflow = PipelineInfoWorkflow(
        dpath_root,
        pipeline_name="example",
        pipeline_version="1.0.0",
    )

    workflow.run_main()

    output = "\n".join(record.message for record in caplog.records)
    assert "example 1.0.0" in output
    assert "example-1.0.0" in output


@pytest.mark.parametrize("pipeline_version", [None, "3.0.0"])
def test_run_main_pipeline_not_found(
    dpath_root: Path,
    pipeline_version: str | None,
):
    pipeline_name = "missing" if pipeline_version is None else "example"
    workflow = PipelineInfoWorkflow(
        dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
    )

    with pytest.raises(WorkflowError, match="No installed pipeline found"):
        workflow.run_main()
