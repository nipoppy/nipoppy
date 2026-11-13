"""Tests for the HPCExecutor class."""

import dataclasses
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_mock

from nipoppy.config.hpc import HpcConfig
from nipoppy.env import PROGRAM_NAME
from nipoppy.exceptions import ReturnCode
from nipoppy.utils.utils import get_pipeline_tag
from nipoppy.workflows.executor import Executor, WorkItem
from nipoppy.workflows.hpc_executor import HPCExecutor, HPCWorkflowContext
from nipoppy.workflows.runner import Runner


@pytest.fixture(scope="function")
def workflow(tmp_path: Path) -> SimpleNamespace:
    """Fake workflow that satisfies HPCWorkflowContext."""
    return SimpleNamespace(
        subcommand="process",
        dpath_root=tmp_path / "study",
        fpath_layout=None,
        pipeline_name="my_pipeline",
        pipeline_version="1.0.0",
        pipeline_step="step1",
        pipeline_step_config=SimpleNamespace(HPC_CONFIG_FILE=None),
        dpath_pipeline_bundle=tmp_path / "bundle",
        dpath_pipeline_work=tmp_path / "work",
        participant_id=None,
        session_id=None,
        keep_workdir=False,
        verbose=False,
        dry_run=False,
        study=SimpleNamespace(
            layout=SimpleNamespace(
                dpath_hpc=tmp_path / "hpc",
                dpath_logs=tmp_path / "logs",
                fpath_curation_status=tmp_path / "curation_status.tsv",
            ),
            config=SimpleNamespace(
                HPC_PREAMBLE=["module load x"], HPC_QUEUE_LIMIT=None
            ),
        ),
        extra_cli_flags=[],
        process_template_json=lambda template_json, **kwargs: template_json,
    )


@pytest.fixture(scope="function")
def executor(workflow: SimpleNamespace) -> HPCExecutor:
    return HPCExecutor(workflow, hpc_cluster="slurm")


def test_work_item_frozen_and_hashable():
    item = WorkItem(participant_id="P01", session_id="1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.participant_id = "P02"
    assert hash(item) == hash(WorkItem("P01", "1"))
    assert {item: "result"}[WorkItem("P01", "1")] == "result"


def test_is_executor(executor: HPCExecutor):
    assert isinstance(executor, Executor)


def test_runner_satisfies_workflow_context(runner: Runner):
    ctx: HPCWorkflowContext = runner  # noqa: F841 (static type check)
    names = list(HPCWorkflowContext.__annotations__) + ["process_template_json"]
    for name in names:
        assert hasattr(runner, name), f"Runner is missing {name}"


@pytest.mark.parametrize("hpc_config_data", [{}, {"CORES": "8", "MEMORY": "32G"}])
def test_load_hpc_config(
    hpc_config_data: dict,
    executor: HPCExecutor,
    workflow: SimpleNamespace,
    tmp_path: Path,
    mocker: pytest_mock.MockFixture,
):
    fpath_hpc_config = tmp_path / "hpc_config.json"
    fpath_hpc_config.write_text(json.dumps(hpc_config_data))
    workflow.pipeline_step_config.HPC_CONFIG_FILE = fpath_hpc_config.name
    workflow.dpath_pipeline_bundle = tmp_path
    workflow.process_template_json = mocker.MagicMock(
        side_effect=lambda template_json, **kwargs: template_json
    )

    hpc_config = executor._load_hpc_config()

    assert hpc_config == HpcConfig(**hpc_config_data)
    # make sure substitutions are processed
    workflow.process_template_json.assert_called_once_with(hpc_config_data)


def test_load_hpc_config_no_file(executor: HPCExecutor):
    assert executor._load_hpc_config() == HpcConfig()


def test_build_hpc_runner(executor: HPCExecutor, workflow: SimpleNamespace):
    hpc_runner = executor._build_hpc_runner(HpcConfig())
    assert hpc_runner.hpc_cluster == "slurm"
    assert hpc_runner.dpath_root == workflow.dpath_root
    assert hpc_runner.dpath_hpc == workflow.study.layout.dpath_hpc
    assert hpc_runner.preamble == ["module load x"]


def _expected_base_command(workflow: SimpleNamespace) -> list[str]:
    return [
        PROGRAM_NAME,
        workflow.subcommand,
        "--study",
        str(workflow.dpath_root),
        "--pipeline",
        workflow.pipeline_name,
        "--pipeline-version",
        workflow.pipeline_version,
        "--pipeline-step",
        workflow.pipeline_step,
    ]


@pytest.mark.parametrize(
    "kwargs,extra_cli_flags,expected_suffix",
    [
        (
            {"participant_id": "P01", "session_id": "1"},
            [],
            ["--participant-id", "P01", "--session-id", "1"],
        ),
        (
            {"participant_id": "P01", "session_id": "1"},
            [],
            ["--participant-id", "P01", "--session-id", "1"],
        ),
        (
            {"participant_id": "P01", "session_id": "1"},
            ["--flag1", "--flag2"],
            ["--participant-id", "P01", "--session-id", "1", "--flag1", "--flag2"],
        ),
        (
            {"participant_id": None, "session_id": "1"},
            ["--tar"],
            ["--session-id", "1", "--tar"],
        ),
    ],
)
def test_generate_cli_command(
    kwargs: dict,
    extra_cli_flags: list[str],
    expected_suffix: list[str],
    workflow: SimpleNamespace,
):
    workflow.extra_cli_flags = extra_cli_flags
    executor = HPCExecutor(workflow, hpc_cluster="slurm")
    assert executor.generate_cli_command(**kwargs) == (
        _expected_base_command(workflow) + expected_suffix
    )


def test_generate_cli_command_keep_workdir(
    workflow: SimpleNamespace,
):
    workflow.keep_workdir = True
    executor = HPCExecutor(workflow, hpc_cluster="slurm")
    command = executor.generate_cli_command(participant_id="P01", session_id="1")
    assert "--keep-workdir" in command


def test_generate_cli_command_verbose(workflow: SimpleNamespace):
    workflow.verbose = True
    executor = HPCExecutor(workflow, hpc_cluster="slurm")
    command = executor.generate_cli_command(participant_id="P01", session_id="1")
    assert "--verbose" in command


def test_generate_cli_command_layout(workflow: SimpleNamespace):
    workflow.fpath_layout = "layout.json"
    executor = HPCExecutor(workflow, hpc_cluster="slurm")
    command = executor.generate_cli_command(participant_id="P01", session_id="1")
    assert command[command.index("--layout") + 1] == "layout.json"


def test_generate_cli_command_fails_duplicate_flags(workflow: SimpleNamespace):
    workflow.keep_workdir = True  # this sets --keep-workdir
    workflow.extra_cli_flags = ["--keep-workdir"]
    executor = HPCExecutor(workflow, hpc_cluster="slurm")
    with pytest.raises(ValueError, match="Flag .* is already in the command"):
        executor.generate_cli_command(participant_id="P01", session_id="1")


@pytest.fixture(scope="function")
def mocked_hpc_runner(mocker: pytest_mock.MockFixture):
    """Patch the HPCRunner class used by the executor."""
    return mocker.patch("nipoppy.workflows.hpc_executor.HPCRunner").return_value


def test_execute(
    executor: HPCExecutor,
    workflow: SimpleNamespace,
    mocked_hpc_runner,
    mocker: pytest_mock.MockFixture,
):
    mocker.patch.object(
        executor,
        "generate_cli_command",
        side_effect=(
            lambda participant_id, session_id: [
                "echo",
                f"{participant_id}, {session_id}",
            ]
        ),
    )
    mocked_hpc_runner.submit.return_value = 2

    items = [WorkItem("participant1", "session1"), WorkItem("participant2", "session2")]
    result = executor.execute(items)

    mocked_hpc_runner.submit.assert_called_once_with(
        job_name=get_pipeline_tag(
            workflow.pipeline_name,
            workflow.pipeline_version,
            workflow.pipeline_step,
            workflow.participant_id,
            workflow.session_id,
        ),
        job_array_commands=[
            "echo 'participant1, session1'",
            "echo 'participant2, session2'",
        ],
        participant_ids=["participant1", "participant2"],
        session_ids=["session1", "session2"],
        dpath_work=workflow.dpath_pipeline_work,
        dpath_hpc_logs=workflow.study.layout.dpath_logs / "hpc",
        pipeline_name=workflow.pipeline_name,
        pipeline_version=workflow.pipeline_version,
        pipeline_step=workflow.pipeline_step,
        dry_run=workflow.dry_run,
    )
    assert result.return_code == ReturnCode.SUCCESS
    assert result.succeeded == items
    assert result.failed == []
    assert result.results == {}


@pytest.mark.parametrize(
    "n_submitted,expected_return_code,expected_level,expected_message",
    [
        (3, ReturnCode.SUCCESS, "SUCCESS", "Successfully submitted 3 HPC job(s)"),
        (
            2,
            ReturnCode.PARTIAL_SUCCESS,
            "WARNING",
            "Submitted 2 out of 3 HPC job(s); the HPC queue limit was reached",
        ),
        (0, ReturnCode.FAILURE, "FAILURE", "Failed to submit HPC jobs"),
    ],
)
@pytest.mark.no_xdist
def test_execute_return_code(
    n_submitted: int,
    expected_return_code: ReturnCode,
    expected_level: str,
    expected_message: str,
    executor: HPCExecutor,
    mocked_hpc_runner,
    caplog: pytest.LogCaptureFixture,
):
    mocked_hpc_runner.submit.return_value = n_submitted

    items = [WorkItem("p1", "s1"), WorkItem("p2", "s2"), WorkItem("p3", "s3")]
    result = executor.execute(items)

    assert result.return_code == expected_return_code
    assert result.succeeded == items[:n_submitted]
    assert result.failed == items[n_submitted:]
    assert expected_message in caplog.text
    if expected_level == "WARNING":
        assert any(
            record.levelname == "WARNING" and expected_message in record.message
            for record in caplog.records
        )


def test_execute_empty(executor: HPCExecutor, mocked_hpc_runner):
    result = executor.execute([])

    assert result.return_code == ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN
    assert result.succeeded == []
    assert result.failed == []
    mocked_hpc_runner.submit.assert_not_called()
