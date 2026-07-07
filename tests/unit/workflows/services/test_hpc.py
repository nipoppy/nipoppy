"""Unit tests for HPCRunner."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.hpc import HpcConfig
from nipoppy.env import PROGRAM_NAME
from nipoppy.study import Study
from nipoppy.workflows.services.hpc import HPCRunner
from tests.conftest import get_config


@pytest.fixture
def hpc_config():
    """Fixture for HpcConfig."""
    return HpcConfig(
        ACCOUNT="test_account",
        TIME="01:00:00",
        MEMORY="4G",
    )


@pytest.fixture(scope="function")
def hpc_runner(study, hpc_config):
    """Fixture for HpcConfig."""
    return HPCRunner(
        study=study,
        hpc_config=hpc_config,
        subcommand="test",
        dpath_root="test",
        pipeline_name="test",
    )


def test_hpc_runner_initialization(study, hpc_runner: HPCRunner, hpc_config: HpcConfig):
    """Test that HPCRunner can be initialized."""
    assert hpc_runner.study is study
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


@pytest.mark.no_xdist
def test_check_hpc_config_unused_vars(
    hpc_runner: HPCRunner, caplog: pytest.LogCaptureFixture
):
    """Test that HPCRunner warns about unused HPC config variables."""
    hpc_runner.hpc_config = HpcConfig(CORES="8", RANDOM_VAR="value")
    hpc_runner._check_hpc_config()
    assert sum(
        [
            (
                ("Found variables in the HPC config that are unused" in record.message)
                and ("RANDOM_VAR" in record.message)
                and record.levelname == "WARNING"
            )
            for record in caplog.records
        ]
    )


def test_hpc_runner_submit(
    hpc_runner: HPCRunner,
    study: Study,
    mocker: pytest_mock.MockerFixture,
    tmp_path: Path,
):
    """Test that HPCRunner can submit a job."""
    # Mock the study config too
    config = get_config(dicom_dir_map_file="[[NIPOPPY_DPATH_ROOT]]")
    mocker.patch("nipoppy.study.Config.load", return_value=config)

    mock_qa = mocker.MagicMock()
    mock_qa.submit_job.return_value = 12345
    mocker.patch("nipoppy.workflows.services.hpc.QueueAdapter", return_value=mock_qa)

    # Needs a directory to not fail the LayoutError
    study.layout.dpath_hpc.mkdir(parents=True, exist_ok=True)

    job_id = hpc_runner.submit(
        hpc_cluster="slurm",
        job_name="my-job",
        job_array_commands=["echo test"],
        participant_ids=["P01"],
        session_ids=["S01"],
        dpath_work=tmp_path / "work",
        dpath_hpc_logs=tmp_path / "logs",
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
        (
            dict(
                participant_id="P01",
                session_id="1",
                extra_flags=["--flag1", "--flag2"],
                extra_options={"--option1": "value1", "--option2": "value2"},
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
                "--option1",
                "value1",
                "--option2",
                "value2",
                "--flag1",
                "--flag2",
            ],
        ),
    ],
)
def test_generate_cli_command(
    hpc_runner: HPCRunner, kwargs: dict, expected_command: list[str]
) -> None:
    """Test HPCRunner.generate_cli_command produces correct CLI tokens."""
    assert hpc_runner.generate_cli_command(**kwargs) == expected_command


def test_generate_cli_keep_workdir(hpc_runner: HPCRunner):
    """Test that --keep-workdir flag is included when keep_workdir is True."""
    hpc_runner.keep_workdir = True
    command = hpc_runner.generate_cli_command(participant_id="P01", session_id="1")
    assert "--keep-workdir" in command


def test_generate_cli_verbose(hpc_runner: HPCRunner):
    """Test that --verbose flag is included when verbose is True."""
    hpc_runner.verbose = True
    command = hpc_runner.generate_cli_command(participant_id="P01", session_id="1")
    assert "--verbose" in command


def test_generate_cli_fails_duplicate_options(hpc_runner: HPCRunner):
    """Test an error is raised when extra_options contains duplicate keys."""
    with pytest.raises(
        ValueError,
        match="Option .* is already set by the default options",
    ):
        hpc_runner.generate_cli_command(
            participant_id="P01",
            session_id="1",
            extra_options={"--participant-id": "P02"},
        )


def test_generate_cli_fails_duplicate_flags(hpc_runner: HPCRunner):
    """Test an error is raised when extra_flags would add a duplicate flag."""
    hpc_runner.keep_workdir = True  # This sets the --keep-workdir
    duplicate_flag = "--keep-workdir"
    with pytest.raises(
        ValueError,
        match="Flag .* is already in the command",
    ):
        hpc_runner.generate_cli_command(
            participant_id="P01",
            session_id="1",
            extra_flags=[duplicate_flag],
        )
