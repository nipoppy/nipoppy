"""Tests for PipelineInfoWorkflow."""

import re
from pathlib import Path

import pytest

from nipoppy.env import PipelineTypeEnum
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
    return workflow


@pytest.mark.no_xdist
def test_run_all_config_files(
    workflow: PipelineInfoWorkflow, caplog: pytest.LogCaptureFixture
):
    """Test that all file paths from all steps are shown, and only those set."""
    workflow.run()

    assert re.search("Step: .*step1", caplog.text)
    assert re.search("Step: .*step2", caplog.text)
    for label, fname in [
        ("Descriptor", "descriptor1.json"),
        ("Invocation", "invocation1.json"),
        ("HPC config", "hpc1.json"),
        ("Tracker config", "tracker1.json"),
        ("PyBIDS ignore", "ignore1.json"),
        ("Descriptor", "descriptor2.json"),
        ("Invocation", "invocation2.json"),
    ]:
        assert re.search(
            f"{label}: .*processing/my_pipeline-1.0.0/{fname}", caplog.text
        )
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
