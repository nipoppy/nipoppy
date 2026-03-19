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


@pytest.fixture(scope="function")
def hpc_runner(study, hpc_config):
    """Fixture for HpcConfig."""
    return HPCRunner(
        context=study,
        hpc_config=hpc_config,
        subcommand="test",
        dpath_root="test",
        pipeline_name="test",
    )


def test_hpc_runner_initialization(study, hpc_runner: HPCRunner, hpc_config: HpcConfig):
    """Test that HPCRunner can be initialized."""
    assert hpc_runner.context is study
    assert hpc_runner.hpc_config is hpc_config


def test_hpc_runner_check_hpc_config(hpc_runner: HPCRunner):
    """Test that HPCRunner can check HPC config correctly."""
    hpc_runner.hpc_config = HpcConfig(CORES="8", MEMORY="32G")
    assert hpc_runner._check_hpc_config() == {"CORES": "8", "MEMORY": "32G"}


@pytest.mark.parametrize("hpc_config", [HpcConfig(), None])
@pytest.mark.no_xdist
def test_hpc_runner_check_hpc_config_empty(
    hpc_runner: HPCRunner, hpc_config: HpcConfig, caplog
):
    """Test empty hpc config."""
    hpc_runner.hpc_config = hpc_config
    hpc_runner._check_hpc_config()
    assert (
        sum("HPC configuration is empty" in record.message for record in caplog.records)
        == 1
    )


def test_hpc_runner_submit(hpc_runner: HPCRunner, study, mocker):
    """Test that HPCRunner can submit a job."""
    # Mock the study config to
    mocked_study_config(mocker)

    mock_qa = mocker.MagicMock()
    mock_qa.submit_job.return_value = 12345
    mocker.patch("nipoppy.workflows.services.hpc.QueueAdapter", return_value=mock_qa)

    # Needs a directory to not fail the LayoutError
    study.layout.dpath_hpc.mkdir(parents=True, exist_ok=True)
    dpath_work = study.layout.dpath_hpc / "work"
    dpath_hpc_logs = study.layout.dpath_hpc / "logs"

    job_id = hpc_runner.submit(
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
                participant_id="P01",
                session_id="1",
            ),
            [
                PROGRAM_NAME,
                "test",
                "--dataset",
                "test",
                "--pipeline",
                "test",
                "--participant-id",
                "P01",
                "--session-id",
                "1",
            ],
        ),
    ],
)
def test_generate_cli_command(
    hpc_runner: HPCRunner, kwargs: dict, expected_command: list[str]
) -> None:
    """Test HPCRunner.generate_cli_command produces correct CLI tokens."""
    assert hpc_runner.generate_cli_command(**kwargs) == expected_command
