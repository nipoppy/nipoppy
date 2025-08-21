"""Tests for PipelineRunner."""

import json
import re
import subprocess
import tarfile
from pathlib import Path

import pytest
import pytest_mock
from bids import BIDSLayout
from fids import fids

from nipoppy.config.container import ContainerConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import ContainerCommandEnum
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.workflows.runner import PipelineRunner
from tests.conftest import (
    create_empty_dataset,
    create_pipeline_config_files,
    get_config,
    prepare_dataset,
)


@pytest.fixture(scope="function")
def runner(tmp_path: Path, mocker: pytest_mock.MockFixture) -> PipelineRunner:
    runner = PipelineRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="dummy_pipeline",
        pipeline_version="1.0.0",
    )

    create_empty_dataset(runner.layout.dpath_root)

    runner.config = get_config(
        container_config={
            "COMMAND": "apptainer",  # mocked
            "ARGS": ["--flag1"],
        },
    )

    mocker.patch(
        "nipoppy.config.container.check_container_command", side_effect=(lambda x: x)
    )

    fname_descriptor = "descriptor.json"
    fname_invocation = "invocation.json"

    fpath_container = tmp_path / "fake_container.sif"
    fpath_container.touch()

    create_pipeline_config_files(
        runner.layout.dpath_pipelines,
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
    return runner


def test_run_setup(runner: PipelineRunner, mocker: pytest_mock.MockFixture):
    mocked_check_tar_conditions = mocker.patch.object(runner, "_check_tar_conditions")
    runner.run_setup()
    assert runner.dpath_pipeline_output.exists()
    assert runner.dpath_pipeline_work.exists()
    mocked_check_tar_conditions.assert_called_once()


@pytest.mark.parametrize("keep_workdir", [True, False])
def test_run_cleanup(runner: PipelineRunner, keep_workdir):
    runner.keep_workdir = keep_workdir
    dpaths = [runner.dpath_pipeline_bids_db, runner.dpath_pipeline_work]
    for dpath in dpaths:
        dpath.mkdir(parents=True)
    runner.run_cleanup()
    for dpath in dpaths:
        if keep_workdir:
            assert dpath.exists()
        else:
            assert not dpath.exists()


@pytest.mark.parametrize("n_success", [1, 2])
def test_run_failed_cleanup(runner: PipelineRunner, n_success):
    runner.keep_workdir = False
    runner.n_success = n_success
    runner.n_total = 2
    dpaths = [runner.dpath_pipeline_bids_db, runner.dpath_pipeline_work]
    for dpath in dpaths:
        dpath.mkdir(parents=True)
    runner.run_cleanup()
    if runner.n_success == runner.n_total:
        assert not dpath.exists()
    else:
        assert dpath.exists()


@pytest.mark.parametrize("simulate", [True, False])
def test_launch_boutiques_run(
    simulate, runner: PipelineRunner, mocker: pytest_mock.MockFixture
):
    runner.simulate = simulate

    participant_id = "01"
    session_id = "BL"

    mocked_run_command = mocker.patch.object(runner, "run_command")

    descriptor_str, invocation_str = runner.launch_boutiques_run(
        participant_id, session_id
    )

    assert "[[NIPOPPY_DPATH_BIDS]]" not in descriptor_str
    assert "[[NIPOPPY_PARTICIPANT_ID]]" not in invocation_str
    assert "[[NIPOPPY_BIDS_SESSION_ID]]" not in invocation_str

    assert mocked_run_command.call_count == 1
    assert mocked_run_command.call_args[1].get("quiet") is True


@pytest.mark.parametrize(
    "container_config,expected_container_opts",
    [
        (None, ["--no-container"]),
        (
            ContainerConfig(),
            [
                "--force-singularity",
                "--no-automount",
                "--imagepath",
                "--container-opts",
            ],
        ),
    ],
)
@pytest.mark.parametrize("simulate", [True, False])
@pytest.mark.parametrize("verbose", [True, False])
def test_launch_boutiques_run_bosh_container_opts(
    container_config,
    expected_container_opts,
    simulate,
    verbose,
    runner: PipelineRunner,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    runner.simulate = simulate
    runner.verbose = verbose
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"

    participant_id = "01"
    session_id = "BL"

    mocked_run_command = mocker.patch.object(runner, "run_command")

    runner.launch_boutiques_run(
        participant_id,
        session_id,
        container_config=container_config,
    )

    if not simulate:
        # first positional argument
        bosh_command_args = mocked_run_command.call_args[0][0]

        for opt in expected_container_opts:
            assert (
                opt in bosh_command_args
            ), f"Expected container option '{opt}' not found in {bosh_command_args}"

        assert ("--debug" in bosh_command_args) == verbose

    else:
        assert "Additional launch options:" in caplog.text
        assert ("--debug" in caplog.text) == verbose


def test_launch_boutiques_run_bosh_no_container_image(
    runner: PipelineRunner,
    mocker: pytest_mock.MockFixture,
):
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"
    runner.descriptor.pop("container-image")

    participant_id = "01"
    session_id = "BL"

    mocked_run_command = mocker.patch.object(runner, "run_command")

    runner.launch_boutiques_run(
        participant_id,
        session_id,
        container_config=ContainerConfig(),
    )

    container_opts = mocked_run_command.call_args[0][0]  # first positional argument
    assert "--no-container" in container_opts


@pytest.mark.parametrize("simulate", [True, False])
def test_launch_boutiques_run_error(
    simulate,
    runner: PipelineRunner,
    mocker: pytest_mock.MockFixture,
):
    runner.simulate = simulate

    participant_id = "01"
    session_id = "BL"

    fids.create_fake_bids_dataset(
        runner.layout.dpath_bids,
        subjects=participant_id,
        sessions=session_id,
    )

    runner.dpath_pipeline_output.mkdir(parents=True, exist_ok=True)
    runner.dpath_pipeline_work.mkdir(parents=True, exist_ok=True)

    mocker.patch.object(
        runner,
        "run_command",
        side_effect=subprocess.CalledProcessError(1, "run_command failed"),
    )

    if simulate:
        expected_message = "Pipeline simulation failed (return code: 1)"
    else:
        expected_message = "Pipeline did not complete successfully (return code: 1)"

    with pytest.raises(RuntimeError, match=re.escape(expected_message)):
        runner.launch_boutiques_run(participant_id, session_id, container_command="")


def test_process_container_config(runner: PipelineRunner, tmp_path: Path):
    bind_path = tmp_path / "to_bind"
    container_command, container_config = runner.process_container_config(
        participant_id="01", session_id="BL", bind_paths=[bind_path]
    )

    # check that the subcommand 'exec' from the Boutiques container config is used
    # note: the container command in the config is "echo" because otherwise the
    # check for the container command fails if Singularity/Apptainer is not on the PATH
    root_path = runner.layout.dpath_root.resolve()
    assert container_command.startswith("apptainer exec")
    assert f"--bind {root_path} " in container_command
    assert container_command.endswith(f"--bind {bind_path.resolve()}")

    # check that the right container config was used
    assert "--flag1" in container_command
    assert "--flag2" in container_command
    assert "--flag3" in container_command

    # check that container config object matches command string
    assert isinstance(container_config, ContainerConfig)
    assert container_config.COMMAND == ContainerCommandEnum.APPTAINER
    assert "--bind" in container_config.ARGS
    assert str(root_path) in container_config.ARGS
    assert str(bind_path.resolve()) in container_config.ARGS
    assert "--flag1" in container_config.ARGS
    assert "--flag2" in container_config.ARGS
    assert "--flag3" in container_config.ARGS


def test_process_container_config_no_bindpaths(runner: PipelineRunner):
    # smoke test for no bind paths
    runner.process_container_config(participant_id="01", session_id="BL")


def test_check_tar_conditions_no_tracker_config(runner: PipelineRunner):
    runner.tar = True
    runner.pipeline_step_config.TRACKER_CONFIG_FILE = None
    with pytest.raises(
        RuntimeError, match="Tarring requested but is no tracker config file"
    ):
        runner._check_tar_conditions()


def test_check_tar_conditions_no_dir(runner: PipelineRunner, tmp_path: Path):
    runner.tar = True
    runner.pipeline_step_config.TRACKER_CONFIG_FILE = tmp_path  # not used
    runner.tracker_config = TrackerConfig(
        PATHS=[tmp_path], PARTICIPANT_SESSION_DIR=None
    )
    with pytest.raises(
        RuntimeError,
        match="Tarring requested but no participant-session directory specified",
    ):
        runner._check_tar_conditions()


def test_check_tar_conditions_no_tar(runner: PipelineRunner):
    runner.tar = False
    runner._check_tar_conditions()


@pytest.mark.parametrize("dpath_type", [Path, str])
def test_tar_directory(tmp_path: Path, dpath_type):
    # create dummy files to tar
    dpath_to_tar = tmp_path / "my_data"
    fpaths_to_tar = [
        dpath_to_tar / "dir1" / "file1.txt",
        dpath_to_tar / "file2.txt",
    ]
    for fpath in fpaths_to_tar:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    runner = PipelineRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="dummy_pipeline",
        pipeline_version="1.0.0",
    )
    fpath_tarred = runner.tar_directory(dpath_type(dpath_to_tar))

    assert fpath_tarred == dpath_to_tar.with_suffix(".tar")
    assert fpath_tarred.exists()
    assert fpath_tarred.is_file()

    with tarfile.open(fpath_tarred, "r") as tar:
        tarred_files = {
            tmp_path / tarred.name for tarred in tar.getmembers() if tarred.isfile()
        }
    assert tarred_files == set(fpaths_to_tar)

    assert not dpath_to_tar.exists()


def test_tar_directory_failure(
    runner: PipelineRunner,
    tmp_path: Path,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    dpath_to_tar = tmp_path / "my_data"
    fpath_to_tar = dpath_to_tar / "file.txt"
    fpath_to_tar.parent.mkdir(parents=True)
    fpath_to_tar.touch()

    mocked_is_tarfile = mocker.patch(
        "nipoppy.workflows.runner.is_tarfile", return_value=False
    )

    fpath_tarred = runner.tar_directory(dpath_to_tar)

    assert fpath_tarred.exists()
    mocked_is_tarfile.assert_called_once()

    assert f"Failed to tar {dpath_to_tar}" in caplog.text


def test_tar_directory_warning_not_found(runner: PipelineRunner):
    with pytest.raises(RuntimeError, match="Not tarring .* since it does not exist"):
        runner.tar_directory("invalid_path")


def test_tar_directory_warning_not_dir(runner: PipelineRunner, tmp_path: Path):
    fpath_to_tar = tmp_path / "file.txt"
    fpath_to_tar.touch()

    with pytest.raises(
        RuntimeError, match="Not tarring .* since it is not a directory"
    ):
        runner.tar_directory(fpath_to_tar)


@pytest.mark.parametrize(
    "curation_status_data,processing_status_data,pipeline_step,expected",
    [
        (
            [
                ["01", "1", False],
                ["01", "2", True],
                ["01", "3", True],
            ],
            None,
            "step1",
            [("01", "2"), ("01", "3")],
        ),
        (
            [
                ["01", "1", False],
                ["01", "2", True],
                ["01", "3", True],
            ],
            [],
            "step1",
            [("01", "2"), ("01", "3")],
        ),
        (
            [
                ["01", "1", False],
                ["01", "2", True],
                ["01", "3", True],
            ],
            [
                [
                    "01",
                    "1",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "01",
                    "2",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "01",
                    "3",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_success,
                ],
            ],
            "step1",
            [],
        ),
        (
            [
                ["01", "1", True],
                ["01", "2", True],
                ["01", "3", True],
            ],
            [
                [
                    "01",
                    "1",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_fail,
                ],
                [
                    "01",
                    "2",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "01",
                    "3",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_fail,
                ],
                [
                    "01",
                    "1",
                    "dummy_pipeline",
                    "2.0",
                    "step1",
                    ProcessingStatusTable.status_success,
                ],
            ],
            "step1",
            [("01", "1"), ("01", "3")],
        ),
        (
            [
                ["01", "1", True],
                ["01", "2", True],
                ["01", "3", True],
            ],
            [
                [
                    "01",
                    "1",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_fail,
                ],
                [
                    "01",
                    "2",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "01",
                    "3",
                    "dummy_pipeline",
                    "1.0.0",
                    "step1",
                    ProcessingStatusTable.status_fail,
                ],
                [
                    "01",
                    "1",
                    "dummy_pipeline",
                    "1.0.0",
                    "step2",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "01",
                    "2",
                    "dummy_pipeline",
                    "1.0.0",
                    "step2",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "01",
                    "3",
                    "dummy_pipeline",
                    "1.0.0",
                    "step2",
                    ProcessingStatusTable.status_fail,
                ],
                [
                    "01",
                    "1",
                    "dummy_pipeline",
                    "2.0",
                    "step1",
                    ProcessingStatusTable.status_success,
                ],
            ],
            "step2",
            [("01", "3")],
        ),
    ],
)
def test_get_participants_sessions_to_run(
    curation_status_data,
    processing_status_data,
    pipeline_step,
    expected,
    runner: PipelineRunner,
):
    participant_id = None
    session_id = None
    runner.pipeline_step = pipeline_step
    runner.participant_id = participant_id
    runner.session_id = session_id

    runner.curation_status_table = CurationStatusTable().add_or_update_records(
        records=[
            {
                CurationStatusTable.col_participant_id: data[0],
                CurationStatusTable.col_session_id: data[1],
                CurationStatusTable.col_visit_id: data[1],
                CurationStatusTable.col_in_bids: data[2],
                CurationStatusTable.col_datatype: None,
                CurationStatusTable.col_participant_dicom_dir: "",
                CurationStatusTable.col_in_pre_reorg: False,
                CurationStatusTable.col_in_post_reorg: False,
            }
            for data in curation_status_data
        ]
    )
    if processing_status_data is not None:
        ProcessingStatusTable(
            processing_status_data,
            columns=[
                ProcessingStatusTable.col_participant_id,
                ProcessingStatusTable.col_session_id,
                ProcessingStatusTable.col_pipeline_name,
                ProcessingStatusTable.col_pipeline_version,
                ProcessingStatusTable.col_pipeline_step,
                ProcessingStatusTable.col_status,
            ],
        ).validate().save_with_backup(runner.layout.fpath_processing_status)

    assert [
        tuple(x)
        for x in runner.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


def test_run_multiple(runner: PipelineRunner):
    participant_id = None
    session_id = None
    runner.participant_id = participant_id
    runner.session_id = session_id

    participants_and_sessions = {"01": ["1"], "02": ["2"]}
    create_empty_dataset(runner.layout.dpath_root)
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=runner.layout.dpath_bids,
    )
    manifest.save_with_backup(runner.layout.fpath_manifest)
    runner.run_setup()
    runner.run_main()

    bids_layout = BIDSLayout(database_path=runner.dpath_pipeline_bids_db)
    assert not len(bids_layout.get(extension=".nii.gz")) == 0


@pytest.mark.parametrize("generate_pybids_database", [True, False])
def test_run_single_pybids_db(
    generate_pybids_database: bool,
    runner: PipelineRunner,
    mocker: pytest_mock.MockFixture,
):
    participant_id = "01"
    session_id = "1"

    # Set GENERATE_PYBIDS_DATABASE
    runner.pipeline_step_config.GENERATE_PYBIDS_DATABASE = generate_pybids_database

    # Mock the set_up_bids_db method
    mocked_set_up_bids_db = mocker.patch.object(runner, "set_up_bids_db")

    # Mock launch_boutiques_run to avoid issues with bosh trying to launch Docker
    mocker.patch.object(runner, "launch_boutiques_run")

    # Call run_single
    runner.run_single(participant_id=participant_id, session_id=session_id)

    # Assert set_up_bids_db was called or not called as expected
    if generate_pybids_database:
        mocked_set_up_bids_db.assert_called_once_with(
            dpath_pybids_db=runner.dpath_pipeline_bids_db,
            participant_id=participant_id,
            session_id=session_id,
        )
    else:
        mocked_set_up_bids_db.assert_not_called()


@pytest.mark.parametrize("tar", [True, False])
@pytest.mark.parametrize("boutiques_success", [True, False])
def test_run_single_tar(
    tar: bool,
    runner: PipelineRunner,
    boutiques_success: bool,
    mocker: pytest_mock.MockFixture,
):
    runner.tar = tar

    # mock the parts of run_single that are not relevant for this test
    mocker.patch(
        "nipoppy.config.container.check_container_command", return_value="apptainer"
    )
    mocker.patch.object(runner, "set_up_bids_db")

    # mock the Boutiques run outcome
    exception_message = "launch_boutiques_run failed"
    mocker.patch.object(
        runner,
        "launch_boutiques_run",
        side_effect=None if boutiques_success else RuntimeError(exception_message),
    )

    # mock tar_directory method (will check if/how this is called)
    mocked_tar_directory = mocker.patch.object(runner, "tar_directory")

    participant_id = "01"
    session_id = "1"
    runner.tracker_config = TrackerConfig(
        PATHS=["fake_path"],  # not used
        PARTICIPANT_SESSION_DIR=(
            "[[NIPOPPY_PARTICIPANT_ID]]_[[NIPOPPY_BIDS_SESSION_ID]]"
        ),
    )
    try:
        runner.run_single(participant_id=participant_id, session_id=session_id)
    except RuntimeError as exception:
        if str(exception) != exception_message:
            raise exception

    if tar and boutiques_success:
        mocked_tar_directory.assert_called_once_with(
            runner.dpath_pipeline_output / f"{participant_id}_ses-{session_id}"
        )
    else:
        mocked_tar_directory.assert_not_called()


def test_run_missing_container_raises_error(runner: PipelineRunner):
    runner.manifest = Manifest()

    runner.pipeline_config.CONTAINER_INFO.FILE = Path("does_not_exist.sif")
    with pytest.raises(FileNotFoundError, match="No container image file found at"):
        runner.run()


@pytest.mark.parametrize(
    "init_params,participant_id,session_id,expected_command",
    [
        (
            {"dpath_root": "/path/to/root", "pipeline_name": "my_pipeline"},
            "P01",
            "1",
            [
                "nipoppy",
                "process",
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
        (
            {
                "dpath_root": "/path/to/other/root",
                "pipeline_name": "other_pipeline",
                "pipeline_version": "1.0.0",
                "pipeline_step": "step1",
                "participant_id": "ShouldNotBeUsed",  # should be skipped
                "session_id": "ShouldNotBeUsed",  # should be skipped
                "simulate": True,  # should be skipped
                "keep_workdir": True,
                "hpc": "slurm",  # should be skipped
                "use_list": "/path/to/list",  # should be skipped
                "tar": True,
                "fpath_layout": "/path/to/layout",
                "dry_run": True,  # should be skipped
                "verbose": True,
            },
            "P01",
            "1",
            [
                "nipoppy",
                "process",
                "--dataset",
                "/path/to/other/root",
                "--pipeline",
                "other_pipeline",
                "--pipeline-version",
                "1.0.0",
                "--pipeline-step",
                "step1",
                "--participant-id",
                "P01",
                "--session-id",
                "1",
                "--keep-workdir",
                "--tar",
                "--layout",
                "/path/to/layout",
                "--verbose",
            ],
        ),
    ],
)
def test_generate_cli_command_for_hpc(
    init_params,
    participant_id,
    session_id,
    expected_command,
    mocker: pytest_mock.MockFixture,
):
    mocker.patch("nipoppy.workflows.base.DatasetLayout")
    runner = PipelineRunner(**init_params)
    assert (
        runner._generate_cli_command_for_hpc(participant_id, session_id)
        == expected_command
    )
