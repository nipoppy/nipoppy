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


def test_hpc_runner_check_hpc_config(workflow_context):
    """Test that HPCRunner can check HPC config correctly."""
    hpc_config = HpcConfig(CORES="8", MEMORY="32G")
    runner = HPCRunner(context=workflow_context, hpc_config=hpc_config)
    assert runner._check_hpc_config() == {"CORES": "8", "MEMORY": "32G"}


@pytest.mark.no_xdist
def test_hpc_runner_check_hpc_config_empty(workflow_context, caplog):
    """Test empty hpc config."""
    runner = HPCRunner(context=workflow_context, hpc_config=HpcConfig())
    runner._check_hpc_config()
    assert (
        sum("HPC configuration is empty" in record.message for record in caplog.records)
        == 1
    )


@pytest.mark.no_xdist
def test_hpc_runner_check_hpc_config_none(workflow_context, caplog):
    """Test None hpc config."""
    runner = HPCRunner(context=workflow_context, hpc_config=None)
    runner._check_hpc_config()
    assert (
        sum("HPC configuration is empty" in record.message for record in caplog.records)
        == 1
    )


def test_hpc_runner_submit(workflow_context, hpc_config, mocker):
    """Test that HPCRunner can submit a job."""
    runner = HPCRunner(context=workflow_context, hpc_config=hpc_config)

    mock_qa = mocker.MagicMock()
    mock_qa.submit_job.return_value = 12345
    mocker.patch("nipoppy.workflows.services.hpc.QueueAdapter", return_value=mock_qa)

    # Needs a directory to not fail the LayoutError
    workflow_context.layout.dpath_hpc.mkdir(parents=True, exist_ok=True)
    dpath_work = workflow_context.layout.dpath_hpc / "work"
    dpath_hpc_logs = workflow_context.layout.dpath_hpc / "logs"

    job_id = runner.submit(
        hpc_cluster="slurm",
        job_name="my-job",
        job_array_commands=["echo test"],
        participant_ids=["P01"],
        session_ids=["S01"],
        dpath_work=dpath_work,
        dpath_hpc_logs=dpath_hpc_logs,
        fname_hpc_error="error.log",
        fname_job_script="script.sh",
        pipeline_name="test-pipe",
        pipeline_version="1.0",
        pipeline_step="step1",
        dry_run=False,
    )

    assert job_id == 12345
    mock_qa.submit_job.assert_called_once()
    args, kwargs = mock_qa.submit_job.call_args
    assert kwargs["NIPOPPY_JOB_NAME"] == "my-job"


def test_hpc_runner_isolated_dependencies():
    """Verify that HPCRunner does not import Boutiques or specific dataset layouts."""
    import sys

    # Just checking the module's imports to ensure no tight coupling
    hpc_module = sys.modules["nipoppy.workflows.services.hpc"]
    assert not hasattr(hpc_module, "bosh"), "HPCRunner should not depend on Boutiques"
    assert "DatasetLayout" not in dir(
        hpc_module
    ), "HPCRunner should not depend directly on layout details beyond Context"
