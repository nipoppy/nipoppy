"""Tests for PipelineValidateWorkflow class."""

import logging

import pytest
import pytest_mock

from nipoppy.workflows.pipeline_store.validate import PipelineValidateWorkflow


@pytest.fixture(scope="function")
def workflow(tmp_path):
    dpath_root = tmp_path / "my_dataset"
    dpath_pipeline = tmp_path / "my_pipeline"
    workflow = PipelineValidateWorkflow(dpath_root, dpath_pipeline)
    return workflow


def test_run_main(
    workflow: PipelineValidateWorkflow,
    mocker: pytest_mock.MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    mocked = mocker.patch(
        "nipoppy.workflows.pipeline_store.validate.check_pipeline_bundle"
    )
    workflow.run_main()

    mocked.assert_called_once_with(
        workflow.pipeline_dir,
        logger=workflow.logger,
        log_level=logging.INFO,
    )

    assert "Validating pipeline at" in caplog.text
    assert "The pipeline files are all valid" in caplog.text
