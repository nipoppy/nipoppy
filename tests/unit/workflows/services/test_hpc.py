"""Unit tests for HPCRunner."""

import pytest

from nipoppy.config.hpc import HpcConfig
from nipoppy.env import PROGRAM_NAME
from nipoppy.workflows.services.hpc import HPCRunner
from tests.conftest import mocked_study_config


@pytest.fixture
def hpc_config():
    """Fixture for HpcConfig."""
    return HpcConfig(
        system="slurm",
        account="test_account",
        walltime="01:00:00",
        memory="4G",
    )


def test_hpc_runner_initialization(study, hpc_config):
    """Test that HPCRunner can be initialized."""
    runner = HPCRunner(context=study, hpc_config=hpc_config)
    assert runner.context is study
    assert runner.hpc_config is hpc_config


def test_hpc_runner_check_hpc_config(study):
    """Test that HPCRunner can check HPC config correctly."""
    hpc_config = HpcConfig(CORES="8", MEMORY="32G")
    runner = HPCRunner(context=study, hpc_config=hpc_config)
    assert runner._check_hpc_config() == {"CORES": "8", "MEMORY": "32G"}


@pytest.mark.no_xdist
def test_hpc_runner_check_hpc_config_empty(study, caplog):
    """Test empty hpc config."""
    runner = HPCRunner(context=study, hpc_config=HpcConfig())
    runner._check_hpc_config()
    assert (
        sum("HPC configuration is empty" in record.message for record in caplog.records)
        == 1
    )


@pytest.mark.no_xdist
def test_hpc_runner_check_hpc_config_none(study, caplog):
    """Test None hpc config."""
    runner = HPCRunner(context=study, hpc_config=None)
    runner._check_hpc_config()
    assert (
        sum("HPC configuration is empty" in record.message for record in caplog.records)
        == 1
    )


def test_hpc_runner_submit(study, hpc_config, mocker):
    """Test that HPCRunner can submit a job."""
    runner = HPCRunner(context=study, hpc_config=hpc_config)

    # Mock the study config to
    mocked_study_config(mocker)

    mock_qa = mocker.MagicMock()
    mock_qa.submit_job.return_value = 12345
    mocker.patch("nipoppy.workflows.services.hpc.QueueAdapter", return_value=mock_qa)

    # Needs a directory to not fail the LayoutError
    study.layout.dpath_hpc.mkdir(parents=True, exist_ok=True)
    dpath_work = study.layout.dpath_hpc / "work"
    dpath_hpc_logs = study.layout.dpath_hpc / "logs"

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


@pytest.mark.parametrize(
    "kwargs,expected_command",
    [
        (
            dict(
                subcommand="bidsify",
                dpath_root="/path/to/root",
                pipeline_name="my_pipeline",
                participant_id="P01",
                session_id="1",
            ),
            [
                PROGRAM_NAME,
                "bidsify",
                "--dataset",
                "/path/to/root",
                "--pipeline",
                "my_pipeline",
                "--participant-id",
                "P01",
                "--session-id",
                "1",
            ],
        ),
    ],
)
def test_generate_cli_command(kwargs: dict, expected_command: list[str]) -> None:
    """Test HPCRunner.generate_cli_command produces correct CLI tokens."""
    assert HPCRunner.generate_cli_command(**kwargs) == expected_command
