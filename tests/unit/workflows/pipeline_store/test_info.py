"""Tests for PipelineInfoWorkflow."""

from pathlib import Path

import pytest

from nipoppy.exceptions import FileOperationError, WorkflowError
from nipoppy.workflows.pipeline_store.info import PipelineInfoWorkflow
from tests.conftest import (
    create_empty_dataset,
    create_pipeline_config_files,
    get_config,
)


@pytest.fixture()
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)
    workflow = PipelineInfoWorkflow(dpath_root, pipeline_name="my_pipeline")
    workflow.study.config = get_config()
    create_pipeline_config_files(
        workflow.study.layout.dpath_pipelines,
        bidsification_pipelines=[
            {
                "NAME": "my_bids_pipeline",
                "VERSION": "1.0.0",
                "STEPS": [{"DESCRIPTOR_FILE": "descriptor.json"}],
            }
        ],
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


class TestRun:
    @pytest.mark.no_xdist
    def test_latest_version(
        self, workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture
    ):
        """Test that the latest installed version is used by default."""
        workflow.run()

        dpath_bundle = (
            workflow.study.layout.dpath_pipelines / "processing/my_pipeline-1.0.0"
        )
        assert "my_pipeline 1.0.0 (processing)" in caplog.text
        assert f"Descriptor: {dpath_bundle / 'descriptor.json'}" in caplog.text
        assert f"Invocation: {dpath_bundle / 'invocation.json'}" in caplog.text

    @pytest.mark.no_xdist
    def test_other_pipeline_type(
        self, workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture
    ):
        """Test that pipelines that are not processing pipelines are found."""
        workflow.pipeline_name = "my_bids_pipeline"

        workflow.run()

        assert "my_bids_pipeline 1.0.0 (bidsification)" in caplog.text

    def test_pipeline_not_installed(self, workflow: PipelineInfoWorkflow):
        """Test that an error is raised if the pipeline is not installed."""
        workflow.pipeline_name = "other_pipeline"
        with pytest.raises(WorkflowError, match="No config found for pipeline"):
            workflow.run()

    def test_version_not_installed(self, workflow: PipelineInfoWorkflow):
        """Test that an error is raised if the version is not installed."""
        workflow.pipeline_version = "2.0.0"
        with pytest.raises(FileOperationError, match="Pipeline config file not found"):
            workflow.run()
