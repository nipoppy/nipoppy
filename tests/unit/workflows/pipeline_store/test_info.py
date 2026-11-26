"""Tests for PipelineInfoWorkflow."""

from pathlib import Path

import pytest

from nipoppy.env import PipelineTypeEnum
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
                "STEPS": [
                    {
                        "DESCRIPTOR_FILE": "descriptor.json",
                        "INVOCATION_FILE": "invocation.json",
                    }
                ],
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


@pytest.mark.no_xdist
def test_run_latest_version(
    workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture
):
    """Test that the latest installed version is used by default."""
    workflow.run()

    dpath_bundle = (
        workflow.study.layout.dpath_pipelines / "processing/my_pipeline-1.0.0"
    )
    fname_config = workflow.study.layout.fname_pipeline_config
    assert "my_pipeline 1.0.0 (processing)" in caplog.text
    assert f"Config: {dpath_bundle / fname_config}" in caplog.text
    assert f"Descriptor: {dpath_bundle / 'descriptor.json'}" in caplog.text
    assert f"Invocation: {dpath_bundle / 'invocation.json'}" in caplog.text


@pytest.mark.no_xdist
def test_run_all_config_files(
    workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture
):
    """Test that all file paths from all steps are shown, and only those set."""
    create_pipeline_config_files(
        workflow.study.layout.dpath_pipelines,
        processing_pipelines=[
            {
                "NAME": "my_full_pipeline",
                "VERSION": "1.0.0",
                "STEPS": [
                    {
                        "NAME": "step1",
                        "DESCRIPTOR_FILE": "descriptor1.json",
                        "INVOCATION_FILE": "invocation1.json",
                        "HPC_CONFIG_FILE": "hpc1.json",
                        "TRACKER_CONFIG_FILE": "tracker1.json",
                        "PYBIDS_IGNORE_FILE": "ignore1.json",
                    },
                    {
                        "NAME": "step2",
                        "DESCRIPTOR_FILE": "descriptor2.json",
                        "INVOCATION_FILE": "invocation2.json",
                    },
                ],
            }
        ],
    )
    workflow.pipeline_name = "my_full_pipeline"

    workflow.run()

    dpath_bundle = (
        workflow.study.layout.dpath_pipelines / "processing/my_full_pipeline-1.0.0"
    )
    assert "Step: step1" in caplog.text
    assert "Step: step2" in caplog.text
    for label, fname in [
        ("Descriptor", "descriptor1.json"),
        ("Invocation", "invocation1.json"),
        ("HPC config", "hpc1.json"),
        ("Tracker config", "tracker1.json"),
        ("PyBIDS ignore", "ignore1.json"),
        ("Descriptor", "descriptor2.json"),
        ("Invocation", "invocation2.json"),
    ]:
        assert f"{label}: {dpath_bundle / fname}" in caplog.text
    # only step1 sets these
    assert caplog.text.count("HPC config:") == 1
    assert caplog.text.count("Tracker config:") == 1
    assert caplog.text.count("PyBIDS ignore:") == 1


@pytest.mark.no_xdist
def test_run_other_pipeline_type(
    workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture
):
    """Test that pipelines that are not processing pipelines are found."""
    workflow.pipeline_name = "my_bids_pipeline"

    workflow.run()

    assert "my_bids_pipeline 1.0.0 (bidsification)" in caplog.text


def test_run_pipeline_not_installed(workflow: PipelineInfoWorkflow):
    """Test that an error is raised if the pipeline is not installed."""
    workflow.pipeline_name = "other_pipeline"
    with pytest.raises(WorkflowError, match="No config found for pipeline"):
        workflow.run()


def test_run_version_not_installed(workflow: PipelineInfoWorkflow):
    """Test that an error is raised if the version is not installed."""
    workflow.pipeline_version = "2.0.0"
    with pytest.raises(FileOperationError, match="Pipeline config file not found"):
        workflow.run()


@pytest.mark.no_xdist
def test_run_variables_not_set(
    workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture
):
    """Test that pipeline variables do not need to be set."""
    # replicate the state right after "nipoppy pipeline install": variables are null
    workflow.study.config.PIPELINE_VARIABLES.set_variables(
        PipelineTypeEnum.PROCESSING, "my_pipeline", "1.0.0", {"MY_VAR": None}
    )

    workflow.run()

    assert "my_pipeline 1.0.0 (processing)" in caplog.text


@pytest.mark.parametrize(
    "method,args",
    [
        ("get_participants_sessions_to_run", (None, None)),
        ("run_single", (None, None)),
    ],
)
def test_loop_methods_not_implemented(workflow: PipelineInfoWorkflow, method, args):
    """Test that the unused participant/session loop methods raise."""
    with pytest.raises(NotImplementedError, match="no participant and session loop"):
        getattr(workflow, method)(*args)
