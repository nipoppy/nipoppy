"""Tests for PipelineInfoWorkflow."""

from pathlib import Path

import pytest

from nipoppy.exceptions import WorkflowError
from nipoppy.workflows.pipeline_store.info import PipelineInfoWorkflow
from tests.conftest import create_empty_dataset, create_pipeline_config_files


@pytest.fixture()
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)
    workflow = PipelineInfoWorkflow(dpath_root, pipeline_name="my_pipeline")
    create_pipeline_config_files(
        workflow.study.layout.dpath_pipelines,
        processing_pipelines=[
            {
                "NAME": "my_pipeline",
                "VERSION": version,
                "STEPS": [
                    {
                        "DESCRIPTOR_FILE": "descriptor.json",
                        "INVOCATION_FILE": "invocation.json",
                    }
                ],
            }
            for version in ["0.9.0", "1.0.0"]
        ],
    )
    return workflow


@pytest.mark.no_xdist
def test_run_main(workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture):
    workflow.run_main()

    # latest version is used by default
    dpath_bundle = (
        workflow.study.layout.dpath_pipelines / "processing/my_pipeline-1.0.0"
    )
    assert f"Bundle: {dpath_bundle}" in caplog.text
    assert f"Descriptor: {dpath_bundle / 'descriptor.json'}" in caplog.text
    assert f"Invocation: {dpath_bundle / 'invocation.json'}" in caplog.text


def test_run_main_pipeline_not_installed(workflow: PipelineInfoWorkflow):
    workflow.pipeline_name = "other_pipeline"
    with pytest.raises(WorkflowError, match="Pipeline other_pipeline is not installed"):
        workflow.run_main()


def test_run_main_version_not_installed(workflow: PipelineInfoWorkflow):
    workflow.pipeline_version = "2.0.0"
    with pytest.raises(WorkflowError, match="Installed versions: 0.9.0, 1.0.0"):
        workflow.run_main()
