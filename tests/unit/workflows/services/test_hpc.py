"""Unit tests for HPCRunner."""

import shutil
from pathlib import Path

import pytest
import pytest_mock
from jinja2 import Environment, meta

from nipoppy.config.hpc import HpcConfig
from nipoppy.env import PROGRAM_NAME
from nipoppy.exceptions import LayoutError, WorkflowError
from nipoppy.study import Study
from nipoppy.utils.utils import DPATH_HPC, FPATH_HPC_TEMPLATE
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
def hpc_runner(hpc_config: HpcConfig, tmp_path: Path) -> HPCRunner:
    """Fixture for HpcConfig."""
    dpath_hpc = tmp_path / "hpc"
    shutil.copytree(DPATH_HPC, dpath_hpc)

    hpc_runner = HPCRunner(
        hpc_cluster="slurm",
        hpc_config=hpc_config,
        subcommand="test",
        dpath_root="test",
        dpath_hpc=dpath_hpc,
        pipeline_name="test",
        preamble=["module load some_module"],
        queue_limit=None,
    )
    return hpc_runner


@pytest.fixture
def submit_kwargs(tmp_path: Path) -> dict:
    """Fixture for HPCRunner.submit() tests that don't care about kwargs."""
    return {
        "job_name": "my-job",
        "job_array_commands": ["echo test", "echo test2"],
        "participant_ids": ["P01", "P02"],
        "session_ids": ["S01", "S01"],
        "dpath_work": tmp_path / "work",
        "dpath_hpc_logs": tmp_path / "logs",
        "fname_hpc_error": "error.log",
        "fname_job_script": "script.sh",
        "pipeline_name": "test-pipe",
        "pipeline_version": "1.0",
        "pipeline_step": "step1",
        "dry_run": False,
    }


@pytest.mark.parametrize(
    "preamble,expected_preamble",
    [
        (["module load some_module"], ["module load some_module"]),
        (None, []),
    ],
)
def test_hpc_runner_initialization(
    preamble, expected_preamble, hpc_config: HpcConfig, tmp_path: Path
):
    """Test that HPCRunner can be initialized."""
    hpc_runner = HPCRunner(
        hpc_cluster="slurm",
        hpc_config=hpc_config,
        subcommand="test",
        dpath_root=tmp_path / "test_study",
        dpath_hpc=tmp_path / "hpc",
        pipeline_name="test",
        preamble=preamble,
    )

    assert hpc_runner.preamble == expected_preamble


def test_hpc_runner_invalid_cluster(hpc_runner: HPCRunner):
    hpc_runner.hpc_cluster = "invalid"

    with pytest.raises(WorkflowError, match="Invalid HPC cluster type"):
        hpc_runner._queue_adapter


def test_hpc_runner_check_hpc_config(hpc_runner: HPCRunner):
    """Test that HPCRunner can check HPC config correctly."""
    hpc_runner.hpc_config = HpcConfig(CORES="8", MEMORY="32G")
    assert hpc_runner._check_hpc_config() == {"CORES": "8", "MEMORY": "32G"}


@pytest.mark.no_xdist
def test_hpc_runner_check_hpc_config_empty(
    hpc_runner: HPCRunner, caplog: pytest.LogCaptureFixture
):
    """Test empty hpc config."""
    hpc_runner.hpc_config = HpcConfig()
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


@pytest.mark.parametrize(
    "queue_limit,n_jobs_in_queue,expected_max_jobs",
    [(10, 0, 10), (10, 4, 6), (5, 5, 0), (2, 3, 0), (0, 1, 0), (-1, 1, 0)],
)
def test_hpc_runner_get_n_available_job_slots(
    queue_limit,
    n_jobs_in_queue,
    expected_max_jobs,
    hpc_runner: HPCRunner,
    mocker: pytest_mock.MockerFixture,
):
    """Test HPCRunner._get_n_available_job_slots()."""
    mock_df = mocker.MagicMock()
    mock_df.__len__ = lambda _: n_jobs_in_queue

    hpc_runner._queue_adapter = mocker.MagicMock()
    hpc_runner._queue_adapter.get_queue_status.return_value = mock_df

    max_jobs = hpc_runner._get_n_available_job_slots(queue_limit=queue_limit)
    assert max_jobs == expected_max_jobs


def test_hpc_runner_get_n_available_job_slots_pysqa_error(
    hpc_runner: HPCRunner, mocker: pytest_mock.MockerFixture
):
    """Test that HPCRunner._get_n_available_job_slots() still runs on pysqa errors."""
    hpc_runner._queue_adapter = mocker.MagicMock()
    hpc_runner._queue_adapter.get_queue_status.side_effect = Exception("pysqa error")

    max_jobs = hpc_runner._get_n_available_job_slots(queue_limit=10)
    assert max_jobs == 10


@pytest.mark.parametrize(
    "hpc_type,hpc_command,queue_limit,n_available_job_slots",
    [("slurm", "sbatch", 10, 2), ("sge", "qsub", 1, 1)],
)
def test_hpc_runner_submit(
    hpc_type: str,
    hpc_command: str,
    queue_limit: int,
    n_available_job_slots: int,
    hpc_runner: HPCRunner,
    submit_kwargs: dict,
    mocker: pytest_mock.MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    """Test that HPCRunner can submit a job."""
    hpc_runner.hpc_cluster = hpc_type
    hpc_runner.queue_limit = queue_limit

    job_id = 12345
    mocked_check_output = mocker.patch(
        "pysqa.base.core.subprocess.check_output", return_value=str(job_id)
    )
    mocked_get_n_available_job_slots = mocker.patch.object(
        hpc_runner, "_get_n_available_job_slots", return_value=n_available_job_slots
    )
    mocked_submit_job = mocker.patch.object(
        hpc_runner._queue_adapter,
        "submit_job",
        wraps=hpc_runner._queue_adapter.submit_job,
    )

    n_submitted_jobs = hpc_runner.submit(**submit_kwargs)

    assert n_submitted_jobs == n_available_job_slots

    mocked_get_n_available_job_slots.assert_called_once_with(hpc_runner.queue_limit)

    mocked_check_output.assert_called_once()
    args, _ = mocked_check_output.call_args
    # check first element of the first positional arg of the subprocess call
    assert args[0][0] == hpc_command

    mocked_submit_job.assert_called_once_with(
        queue=hpc_runner.hpc_cluster,
        working_directory=str(submit_kwargs["dpath_work"]),
        command="",
        cores=0,
        NIPOPPY_HPC=hpc_runner.hpc_cluster,
        NIPOPPY_JOB_NAME=submit_kwargs["job_name"],
        NIPOPPY_DPATH_LOGS=submit_kwargs["dpath_hpc_logs"],
        NIPOPPY_HPC_PREAMBLE_STRINGS=hpc_runner.preamble,
        NIPOPPY_COMMANDS=submit_kwargs["job_array_commands"][:n_available_job_slots],
        NIPOPPY_DPATH_ROOT=hpc_runner.dpath_root,
        NIPOPPY_PIPELINE_NAME=submit_kwargs["pipeline_name"],
        NIPOPPY_PIPELINE_VERSION=submit_kwargs["pipeline_version"],
        NIPOPPY_PIPELINE_STEP=submit_kwargs["pipeline_step"],
        NIPOPPY_PARTICIPANT_IDS=submit_kwargs["participant_ids"][
            :n_available_job_slots
        ],
        NIPOPPY_SESSION_IDS=submit_kwargs["session_ids"][:n_available_job_slots],
        **hpc_runner._check_hpc_config(),
    )
    assert f"HPC job ID: {job_id}" in caplog.text

    template_ast = Environment().parse(FPATH_HPC_TEMPLATE.read_text())
    template_vars = meta.find_undeclared_variables(template_ast)
    nipoppy_args = [
        arg for arg in mocked_submit_job.call_args[1] if arg.startswith("NIPOPPY_")
    ]
    for arg in nipoppy_args:
        assert arg in template_vars, f"Variable {arg} not found in the template"


def test_hpc_runner_submit_no_queue_limit(
    hpc_runner: HPCRunner, submit_kwargs: dict, mocker: pytest_mock.MockerFixture
):
    """Test that HPCRunner.submit() works when queue_limit is None."""
    hpc_runner.queue_limit = None

    mocker.patch("pysqa.base.core.subprocess.check_output", return_value="12345")
    mocked_get_n_available_job_slots = mocker.patch.object(
        hpc_runner, "_get_n_available_job_slots"
    )
    mocker.patch.object(
        hpc_runner._queue_adapter,
        "submit_job",
        wraps=hpc_runner._queue_adapter.submit_job,
    )

    n_submitted_jobs = hpc_runner.submit(**submit_kwargs)

    mocked_get_n_available_job_slots.assert_not_called()
    assert n_submitted_jobs == 2


def test_hpc_runner_submit_no_jobs(
    hpc_runner: HPCRunner, submit_kwargs: dict, mocker: pytest_mock.MockerFixture
):
    """Test that HPCRunner.submit() does not submit when there are no jobs."""
    hpc_runner.queue_limit = 10  # cannot be None
    mocker.patch.object(hpc_runner, "_get_n_available_job_slots", return_value=0)
    mocked_submit_job = mocker.patch.object(hpc_runner._queue_adapter, "submit_job")

    n_submitted_jobs = hpc_runner.submit(**submit_kwargs)
    assert n_submitted_jobs == 0
    mocked_submit_job.assert_not_called()


def test_hpc_runner_submit_creates_logdir(
    hpc_runner: HPCRunner, submit_kwargs: dict, mocker: pytest_mock.MockerFixture
):
    dpath_logs = submit_kwargs["dpath_hpc_logs"]

    mocker.patch.object(hpc_runner._queue_adapter, "submit_job")

    # check that logs directory is created
    assert not (dpath_logs).exists()
    hpc_runner.submit(**submit_kwargs)
    assert dpath_logs.exists()


@pytest.mark.parametrize(
    "write_job_script,expected_message",
    [(True, "Job script created at "), (False, "No job script found at ")],
)
@pytest.mark.no_xdist
def test_hpc_runner_submit_logs_job_script(
    write_job_script: bool,
    expected_message,
    hpc_runner: HPCRunner,
    submit_kwargs: dict,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    def touch_job_script(*args, **kwargs):
        fpath_script = submit_kwargs["dpath_work"] / submit_kwargs["fname_job_script"]
        fpath_script.parent.mkdir(parents=True, exist_ok=True)
        fpath_script.touch()

    mocked_submit_job = mocker.patch.object(hpc_runner._queue_adapter, "submit_job")
    if write_job_script:
        mocked_submit_job.side_effect = touch_job_script

    hpc_runner.submit(**submit_kwargs)
    assert expected_message in caplog.text


@pytest.mark.no_xdist
def test_hpc_runner_submit_no_job_id(
    hpc_runner: HPCRunner,
    submit_kwargs: dict,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    mocker.patch.object(hpc_runner._queue_adapter, "submit_job", return_value=None)

    hpc_runner.submit(**submit_kwargs)
    assert "HPC job ID" not in caplog.text


def test_hpc_runner_submit_pysqa_error(
    hpc_runner: HPCRunner, submit_kwargs: dict, mocker: pytest_mock.MockFixture
):
    def write_error_file(*args, **kwargs):
        fpath_error = submit_kwargs["dpath_work"] / submit_kwargs["fname_hpc_error"]
        fpath_error.parent.mkdir(parents=True, exist_ok=True)
        fpath_error.write_text("PYSQA ERROR\n")

    mocker.patch.object(
        hpc_runner._queue_adapter, "submit_job", side_effect=write_error_file
    )
    with pytest.raises(
        RuntimeError, match="Error occurred while submitting the HPC job:\nPYSQA ERROR"
    ):
        hpc_runner.submit(**submit_kwargs)


def test_hpc_runner_submit_error_no_dir(hpc_runner: HPCRunner, submit_kwargs: dict):
    # remove the HPC config directory
    if hpc_runner.dpath_hpc.exists():
        shutil.rmtree(hpc_runner.dpath_hpc)
    assert not hpc_runner.dpath_hpc.exists()

    with pytest.raises(
        LayoutError,
        match="The HPC directory with appropriate content needs to exist",
    ):
        hpc_runner.submit(**submit_kwargs)


@pytest.mark.parametrize(
    "kwargs,expected_command",
    [
        (
            {"participant_id": "P01", "session_id": "1"},
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
            {
                "participant_id": "P01",
                "session_id": "1",
                "extra_flags": ["--flag1", "--flag2"],
                "extra_options": {"--option1": "value1", "--option2": "value2"},
            },
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
def test_hpc_runner_generate_cli_command(
    hpc_runner: HPCRunner, kwargs: dict, expected_command: list[str]
) -> None:
    """Test HPCRunner.generate_cli_command produces correct CLI tokens."""
    assert hpc_runner.generate_cli_command(**kwargs) == expected_command


def test_hpc_runner_generate_cli_keep_workdir(hpc_runner: HPCRunner):
    """Test that --keep-workdir flag is included when keep_workdir is True."""
    hpc_runner.keep_workdir = True
    command = hpc_runner.generate_cli_command(participant_id="P01", session_id="1")
    assert "--keep-workdir" in command


def test_hpc_runner_generate_cli_verbose(hpc_runner: HPCRunner):
    """Test that --verbose flag is included when verbose is True."""
    hpc_runner.verbose = True
    command = hpc_runner.generate_cli_command(participant_id="P01", session_id="1")
    assert "--verbose" in command


def test_hpc_runner_generate_cli_fails_duplicate_options(hpc_runner: HPCRunner):
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


def test_hpc_runner_generate_cli_fails_duplicate_flags(hpc_runner: HPCRunner):
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
