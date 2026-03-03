"""Unit tests for HPCRunner."""

import pytest

from nipoppy.config.hpc import HpcConfig
from nipoppy.config.main import Config
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.workflows.services.context import WorkflowContext
from nipoppy.workflows.services.hpc import HPCRunner


@pytest.fixture
def workflow_context(tmp_path):
    """Fixture for WorkflowContext."""
    layout = DatasetLayout(tmp_path)
    logger = get_logger("test_logger")
    config = Config()
    return WorkflowContext(layout=layout, logger=logger, config=config)


@pytest.fixture
def hpc_config():
    """Fixture for HpcConfig."""
    return HpcConfig(
        system="slurm",
        account="test_account",
        walltime="01:00:00",
        memory="4G",
    )


def test_hpc_runner_initialization(workflow_context, hpc_config):
    """Test that HPCRunner can be initialized."""
    runner = HPCRunner(context=workflow_context, hpc_config=hpc_config)
    assert runner.context is workflow_context
    assert runner.hpc_config is hpc_config


def test_hpc_runner_generate_script(workflow_context, hpc_config):
    """Test that HPCRunner can generate a submission script."""
    runner = HPCRunner(context=workflow_context, hpc_config=hpc_config)
    job_params = {"command": "echo 'Hello World'"}
    script = runner.generate_script(job_params)
    assert "echo 'Hello World'" in script
    assert "test_account" in script


def test_hpc_runner_submit(workflow_context, hpc_config, mocker):
    """Test that HPCRunner can submit a job."""
    runner = HPCRunner(context=workflow_context, hpc_config=hpc_config)
    job_params = {"command": "echo 'Hello World'"}

    # Mock the actual submission logic
    mock_submit = mocker.patch(
        "nipoppy.workflows.services.hpc.HPCRunner._submit_to_scheduler",
        return_value="12345",
    )

    job_id = runner.submit(job_params)

    assert job_id == "12345"
    mock_submit.assert_called_once()

    # Verify the argument passed to _submit_to_scheduler is the generated script
    expected_script = runner.generate_script(job_params)
    mock_submit.assert_called_with(expected_script)


def test_hpc_runner_isolated_dependencies():
    """Verify that HPCRunner does not import Boutiques or specific dataset layouts."""
    import sys

    # Just checking the module's imports to ensure no tight coupling
    hpc_module = sys.modules["nipoppy.workflows.services.hpc"]
    assert not hasattr(hpc_module, "bosh"), "HPCRunner should not depend on Boutiques"
    assert "DatasetLayout" not in dir(
        hpc_module
    ), "HPCRunner should not depend directly on layout details beyond Context"
