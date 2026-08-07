"""Tests for the Runner class."""

import json
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.hpc import HpcConfig
from nipoppy.utils.utils import get_pipeline_tag
from nipoppy.workflows.processing_runner import ProcessingRunner
from tests.conftest import (
    _set_up_substitution_testing,
    create_empty_dataset,
    create_pipeline_config_files,
    get_config,
    prepare_dataset,
)


@pytest.fixture(scope="function")
def runner(study, tmp_path: Path, mocker: pytest_mock.MockFixture) -> ProcessingRunner:
    runner = ProcessingRunner(
        dpath_root=study.layout.dpath_root,
        pipeline_name="dummy_pipeline",
        pipeline_version="1.0.0",
    )
    runner.study = study

    create_empty_dataset(runner.study.layout.dpath_root)

    runner.study.config = get_config(
        container_config={
            "COMMAND": "apptainer",  # mocked
            "ARGS": ["--flag1"],
        },
    )

    mocker.patch(
        "nipoppy.container.shutil.which",
        side_effect=(lambda command: command),
    )

    fname_descriptor = "descriptor.json"
    fname_invocation = "invocation.json"

    fpath_container = tmp_path / "fake_container.sif"
    fpath_container.touch()

    create_pipeline_config_files(
        runner.study.layout.dpath_pipelines,
        processing_pipelines=[
            {
                "NAME": "dummy_pipeline",
                "VERSION": "1.0.0",
                "CONTAINER_CONFIG": {"ARGS": ["--flag2"]},
                "CONTAINER_INFO": {
                    "FILE": str(fpath_container),
                    "URI": "docker://dummy/image:1.0.0",
                },
                "STEPS": [
                    {
                        "DESCRIPTOR_FILE": fname_descriptor,
                        "INVOCATION_FILE": fname_invocation,
                        "CONTAINER_CONFIG": {"ARGS": ["--flag3"]},
                    },
                ],
            },
        ],
    )

    descriptor = {
        "name": "dummy_pipeline",
        "tool-version": "1.0.0",
        "description": "A dummy pipeline for testing",
        "schema-version": "0.5",
        "command-line": "echo [ARG1] [ARG2] [[NIPOPPY_DPATH_BIDS]]",
        "container-image": {
            "image": "dummy/image",
            "type": "docker",
        },
        "inputs": [
            {
                "id": "arg1",
                "name": "arg1",
                "type": "String",
                "command-line-flag": "--arg1",
                "value-key": "[ARG1]",
            },
            {
                "id": "arg2",
                "name": "arg2",
                "type": "Number",
                "command-line-flag": "--arg2",
                "value-key": "[ARG2]",
            },
        ],
        "custom": {"nipoppy": {"CONTAINER_SUBCOMMAND": "exec"}},
    }
    invocation = {
        "arg1": "[[NIPOPPY_PARTICIPANT_ID]] [[NIPOPPY_BIDS_SESSION_ID]]",
        "arg2": 10,
    }
    (runner.dpath_pipeline_bundle / fname_descriptor).write_text(json.dumps(descriptor))
    (runner.dpath_pipeline_bundle / fname_invocation).write_text(json.dumps(invocation))

    participants_and_sessions = {"01": ["1", "2", "3"], "02": ["1"]}
    create_empty_dataset(runner.study.layout.dpath_root)
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=runner.study.layout.dpath_bids,
    )
    manifest.save_with_backup(runner.study.layout.fpath_manifest)
    return runner


@pytest.mark.parametrize("hpc_config_data", [{}, {"CORES": "8", "MEMORY": "32G"}])
def test_hpc_config(
    hpc_config_data: dict,
    runner: ProcessingRunner,
    tmp_path: Path,
    mocker: pytest_mock.MockFixture,
):
    fpath_hpc_config = tmp_path / "hpc_config.json"
    fpath_hpc_config.write_text(json.dumps(hpc_config_data))

    runner.pipeline_step_config.HPC_CONFIG_FILE = fpath_hpc_config.name
    runner.dpath_pipeline_bundle = fpath_hpc_config.parent

    mocked_process_template_json = _set_up_substitution_testing(runner, mocker)

    assert isinstance(runner.hpc_config, HpcConfig)

    # make sure substitutions are processed
    mocked_process_template_json.assert_called_once()


def test_hpc_config_no_file(runner: ProcessingRunner):
    runner.pipeline_step_config.HPC_CONFIG_FILE = None
    assert runner.hpc_config == HpcConfig()


@pytest.mark.parametrize("queue_limit,expected_n_jobs", [(None, 2), (1, 1), (3, 2)])
def test_submit_hpc_job(
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
    queue_limit: int | None,
    expected_n_jobs: int,
):

    runner.study.config.HPC_QUEUE_LIMIT = queue_limit

    mocker.patch.object(runner.hpc_runner, "_get_max_n_jobs", return_value=queue_limit)
    mocker.patch.object(
        runner,
        "_generate_cli_command_for_hpc",
        side_effect=(
            lambda participant_id, session_id: [
                "echo",
                f"{participant_id}, {session_id}",
            ]
        ),
    )
    mocked_submit = mocker.patch.object(runner.hpc_runner, "submit", return_value=12345)

    participant_ids = ["participant1", "participant2"]
    session_ids = ["session1", "session2"]
    participants_sessions = list(zip(participant_ids, session_ids))
    runner._submit_hpc_job(participants_sessions)

    mocked_submit.assert_called_once_with(
        job_name=get_pipeline_tag(
            runner.pipeline_name,
            runner.pipeline_version,
            runner.pipeline_step,
            runner.participant_id,
            runner.session_id,
        ),
        job_array_commands=[
            "echo 'participant1, session1'",
            "echo 'participant2, session2'",
        ][:expected_n_jobs],
        participant_ids=participant_ids[:expected_n_jobs],
        session_ids=session_ids[:expected_n_jobs],
        dpath_work=runner.dpath_pipeline_work,
        dpath_hpc_logs=runner.study.layout.dpath_logs / runner.dname_hpc_logs,
        fname_hpc_error=runner.fname_hpc_error,
        fname_job_script=runner.fname_job_script,
        pipeline_name=runner.pipeline_name,
        pipeline_version=runner.pipeline_version,
        pipeline_step=runner.pipeline_step,
        dry_run=runner.dry_run,
    )

    assert runner.n_success == expected_n_jobs
    assert runner.n_total == 2


def test_submit_hpc_job_no_jobs(
    runner: ProcessingRunner, mocker: pytest_mock.MockFixture
):
    mocked_submit = mocker.patch.object(runner.hpc_runner, "submit")
    runner._submit_hpc_job([])
    assert not mocked_submit.called


def test_run_main_hpc(mocker: pytest_mock.MockFixture, runner: ProcessingRunner):
    mocker.patch("os.makedirs", mocker.MagicMock())
    mocked_submit_hpc_job = mocker.patch.object(runner, "_submit_hpc_job")

    runner.hpc = "exists"

    runner.run_main()

    mocked_submit_hpc_job.assert_called_once()

    assert list(mocked_submit_hpc_job.call_args[0][0]) == [
        ("01", "1"),
        ("01", "2"),
        ("01", "3"),
        ("02", "1"),
    ]


@pytest.mark.parametrize(
    "tar, extra_flags",
    [
        (True, ["--tar"]),
        (False, None),
    ],
)
def test_generate_cli_command_for_hpc(
    tar: bool,
    extra_flags: list[str] | None,
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
):
    mocked_generate_cli_command = mocker.patch.object(
        runner.hpc_runner,
        "generate_cli_command",
    )
    runner.tar = tar
    runner._generate_cli_command_for_hpc("p01", "s01")
    mocked_generate_cli_command.assert_called_once_with(
        participant_id="p01", session_id="s01", extra_flags=extra_flags
    )
