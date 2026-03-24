"""Tests for PipelineRunner."""

import json
import tarfile
from pathlib import Path
from typing import Optional

import pytest
import pytest_mock
from bids import BIDSLayout
from jinja2 import Environment, meta

from nipoppy.config.hpc import HpcConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.container import (
    ApptainerHandler,
    ContainerHandler,
    DockerHandler,
    SingularityHandler,
)
from nipoppy.env import ContainerCommandEnum
from nipoppy.exceptions import (
    ConfigError,
    FileOperationError,
    WorkflowError,
)
from nipoppy.layout import LayoutError
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils import fileops
from nipoppy.utils.utils import DPATH_HPC, FPATH_HPC_TEMPLATE, get_pipeline_tag
from nipoppy.workflows.processing_runner import ProcessingRunner
from tests.conftest import (
    _set_up_substitution_testing,
    create_empty_dataset,
    create_pipeline_config_files,
    get_config,
    prepare_dataset,
)


@pytest.fixture(scope="function")
def runner(tmp_path: Path, mocker: pytest_mock.MockFixture) -> ProcessingRunner:
    runner = ProcessingRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="dummy_pipeline",
        pipeline_version="1.0.0",
    )

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
    return runner


def test_run_setup(runner: ProcessingRunner, mocker: pytest_mock.MockFixture):
    mocked_check_tar_conditions = mocker.patch.object(runner, "_check_tar_conditions")
    runner.run_setup()
    assert runner.dpath_pipeline_output.exists()
    assert runner.dpath_pipeline_work.exists()
    mocked_check_tar_conditions.assert_called_once()


@pytest.mark.parametrize("keep_workdir", [True, False])
def test_run_cleanup(runner: ProcessingRunner, keep_workdir):
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
def test_run_failed_cleanup(runner: ProcessingRunner, n_success):
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
    simulate, runner: ProcessingRunner, mocker: pytest_mock.MockFixture
):
    runner.simulate = simulate

    participant_id = "01"
    session_id = "BL"

    mocked_run_command = mocker.patch("nipoppy.workflows.runner._run_command")

    descriptor_str, invocation_str = runner.launch_boutiques_run(
        participant_id, session_id
    )

    assert "[[NIPOPPY_DPATH_BIDS]]" not in descriptor_str
    assert "[[NIPOPPY_PARTICIPANT_ID]]" not in invocation_str
    assert "[[NIPOPPY_BIDS_SESSION_ID]]" not in invocation_str

    assert mocked_run_command.call_count == 1
    assert mocked_run_command.call_args[1].get("quiet") is True


@pytest.mark.parametrize(
    "container_handler,expected_container_opts",
    [
        (None, ["--no-container"]),
        (
            ApptainerHandler(),
            [
                "--force-singularity",
                "--no-automount",
                "--imagepath",
                "--container-opts=",
            ],
        ),
        (
            SingularityHandler(),
            [
                "--force-singularity",
                "--no-automount",
                "--imagepath",
                "--container-opts=",
            ],
        ),
        (
            DockerHandler(),
            [
                "--force-docker",
                "--no-automount",
                "--container-opts=",
            ],
        ),
    ],
)
@pytest.mark.parametrize("simulate", [True, False])
@pytest.mark.parametrize("verbose", [True, False])
@pytest.mark.no_xdist
def test_launch_boutiques_run_bosh_opts(
    container_handler,
    expected_container_opts,
    simulate,
    verbose,
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    runner.simulate = simulate
    runner.verbose = verbose
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"

    participant_id = "01"
    session_id = "BL"

    mocked_run_command = mocker.patch("nipoppy.workflows.runner._run_command")

    runner.launch_boutiques_run(
        participant_id,
        session_id,
        container_handler=container_handler,
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
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
):
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"
    runner.descriptor.pop("container-image")

    participant_id = "01"
    session_id = "BL"

    mocked_run_command = mocker.patch("nipoppy.workflows.runner._run_command")

    runner.launch_boutiques_run(
        participant_id,
        session_id,
        container_handler=None,
    )

    container_opts = mocked_run_command.call_args[0][0]  # first positional argument
    assert "--no-container" in container_opts


def test_process_container_config(runner: ProcessingRunner, tmp_path: Path):
    bind_path = tmp_path / "to_bind"
    container_command, container_handler = runner.process_container_config(
        participant_id="01", session_id="BL", bind_paths=[bind_path]
    )

    # check that the subcommand 'exec' from the Boutiques container config is used
    # note: the container command in the config is "echo" because otherwise the
    # check for the container command fails if Singularity/Apptainer is not on the PATH
    root_path = runner.study.layout.dpath_root.resolve()
    assert container_command.startswith("apptainer exec")
    assert f"--bind {root_path}:{root_path}:rw " in container_command
    assert container_command.endswith(
        f"--bind {bind_path.resolve()}:{bind_path.resolve()}:rw"
    )

    # check that the right container config was used
    assert "--flag1" in container_command
    assert "--flag2" in container_command
    assert "--flag3" in container_command

    # check that container config object matches command string
    assert isinstance(container_handler, ContainerHandler)
    assert container_handler.command == ContainerCommandEnum.APPTAINER.value
    assert "--bind" in container_handler.args
    assert f"{root_path}:{root_path}:rw" in container_handler.args
    assert f"{bind_path.resolve()}:{bind_path.resolve()}:rw" in container_handler.args
    assert "--flag1" in container_handler.args
    assert "--flag2" in container_handler.args
    assert "--flag3" in container_handler.args


def test_process_container_config_no_bind_cwd(
    runner: ProcessingRunner, tmp_path: Path, mocker: pytest_mock.MockFixture
):
    bind_path = tmp_path / "to_bind"
    mocker.patch("pathlib.Path.cwd", return_value=bind_path)
    container_command, _ = runner.process_container_config(
        participant_id="01", session_id="BL", bind_paths=[bind_path]
    )

    assert (
        f"--bind {bind_path.resolve()}:{bind_path.resolve()}:rw"
        not in container_command
    )


def test_process_container_config_no_bindpaths(runner: ProcessingRunner):
    # smoke test for no bind paths
    runner.process_container_config(participant_id="01", session_id="BL")


def test_check_tar_conditions_no_tracker_config(runner: ProcessingRunner):
    runner.tar = True
    runner.pipeline_step_config.TRACKER_CONFIG_FILE = None
    with pytest.raises(
        ConfigError,
        match="Tarring requested but there is no tracker config file",
    ):
        runner._check_tar_conditions()


def test_check_tar_conditions_no_dir(runner: ProcessingRunner, tmp_path: Path):
    runner.tar = True
    runner.pipeline_step_config.TRACKER_CONFIG_FILE = tmp_path  # not used
    runner.tracker_config = TrackerConfig(
        PATHS=[tmp_path], PARTICIPANT_SESSION_DIR=None
    )
    with pytest.raises(
        ConfigError,
        match="Tarring requested but no participant-session directory specified",
    ):
        runner._check_tar_conditions()


def test_check_tar_conditions_no_tar(runner: ProcessingRunner):
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

    runner = ProcessingRunner(
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


@pytest.mark.no_xdist
def test_tar_directory_failure(
    runner: ProcessingRunner,
    tmp_path: Path,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    dpath_to_tar = tmp_path / "my_data"
    fpath_to_tar = dpath_to_tar / "file.txt"
    fpath_to_tar.parent.mkdir(parents=True)
    fpath_to_tar.touch()

    mocked_is_tarfile = mocker.patch(
        "nipoppy.workflows.processing_runner.is_tarfile", return_value=False
    )

    fpath_tarred = runner.tar_directory(dpath_to_tar)

    assert fpath_tarred.exists()
    mocked_is_tarfile.assert_called_once()

    assert f"Failed to tar {dpath_to_tar}" in caplog.text


def test_tar_directory_warning_not_found(runner: ProcessingRunner):
    with pytest.raises(
        FileOperationError, match="Not tarring .* since it does not exist"
    ):
        runner.tar_directory("invalid_path")


def test_tar_directory_warning_not_dir(runner: ProcessingRunner, tmp_path: Path):
    fpath_to_tar = tmp_path / "file.txt"
    fpath_to_tar.touch()

    with pytest.raises(
        FileOperationError, match="Not tarring .* since it is not a directory"
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
    runner: ProcessingRunner,
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
        ).validate().save_with_backup(runner.study.layout.fpath_processing_status)

    assert [
        tuple(x)
        for x in runner.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


def test_run_multiple(runner: ProcessingRunner):
    participant_id = None
    session_id = None
    runner.participant_id = participant_id
    runner.session_id = session_id

    participants_and_sessions = {"01": ["1"], "02": ["2"]}
    create_empty_dataset(runner.study.layout.dpath_root)
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=runner.study.layout.dpath_bids,
    )
    manifest.save_with_backup(runner.study.layout.fpath_manifest)
    runner.run_setup()
    runner.run_main()

    bids_layout = BIDSLayout(database_path=runner.dpath_pipeline_bids_db)
    assert not len(bids_layout.get(extension=".nii.gz")) == 0


@pytest.mark.parametrize("generate_pybids_database", [True, False])
def test_run_single_pybids_db(
    generate_pybids_database: bool,
    runner: ProcessingRunner,
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
    runner: ProcessingRunner,
    boutiques_success: bool,
    mocker: pytest_mock.MockFixture,
):
    runner.tar = tar

    # mock the parts of run_single that are not relevant for this test
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


def test_run_missing_container_raises_error(runner: ProcessingRunner):
    runner.study.manifest = Manifest()

    runner.pipeline_config.CONTAINER_INFO.FILE = Path("does_not_exist.sif")
    with pytest.raises(
        FileOperationError, match="No container image file found for pipeline"
    ):
        runner.run()


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


def _set_up_hpc_for_testing(
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
    mock_pysqa=True,
):
    # set HPC attribute to something valid
    runner.hpc = "slurm"

    # copy HPC config files
    fileops.copy(DPATH_HPC, runner.study.layout.dpath_hpc)

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

    # mock PySQA job submission function
    if mock_pysqa:
        mock_submit_job = mocker.patch("pysqa.QueueAdapter.submit_job")
        return mock_submit_job


@pytest.mark.parametrize("hpc_type,hpc_command", [("slurm", "sbatch"), ("sge", "qsub")])
@pytest.mark.no_xdist
def test_submit_hpc_job(
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
    hpc_type: str,
    hpc_command: str,
):
    job_id = "12345"
    hpc_config = {
        "CORES": "8",
        "MEMORY": "32G",
    }
    _set_up_hpc_for_testing(runner, mocker, mock_pysqa=False)
    runner.hpc = hpc_type

    mocker.patch(
        "nipoppy.workflows.services.hpc.HPCRunner._check_hpc_config",
        return_value=hpc_config,
    )
    mocked_check_output = mocker.patch(
        "pysqa.base.core.subprocess.check_output", return_value=job_id
    )
    participants_sessions = [("participant1", "session1"), ("participant2", "session2")]

    runner._submit_hpc_job(participants_sessions)

    mocked_check_output.assert_called_once()
    # positional arguments, index 0, first element of the list
    assert mocked_check_output.call_args[0][0][0] == hpc_command

    assert f"HPC job ID: {job_id}" in caplog.text


def test_submit_hpc_job_no_dir(
    runner: ProcessingRunner, mocker: pytest_mock.MockFixture
):
    _set_up_hpc_for_testing(runner, mocker)

    # remove the directory created by _set_up_hpc_for_testing
    import shutil

    if runner.study.layout.dpath_hpc.exists():
        shutil.rmtree(runner.study.layout.dpath_hpc)

    assert not runner.study.layout.dpath_hpc.exists()
    with pytest.raises(
        LayoutError,
        match="The HPC directory with appropriate content needs to exist",
    ):
        runner._submit_hpc_job([("P1", "1")])


def test_submit_hpc_job_invalid_hpc(
    runner: ProcessingRunner, mocker: pytest_mock.MockFixture
):
    _set_up_hpc_for_testing(runner, mocker)
    runner.hpc = "invalid"

    with pytest.raises(WorkflowError, match="Invalid HPC cluster type"):
        runner._submit_hpc_job([("P1", "1")])


def test_submit_hpc_job_logs(runner: ProcessingRunner, mocker: pytest_mock.MockFixture):
    _set_up_hpc_for_testing(runner, mocker)

    dpath_logs = runner.study.layout.dpath_logs / runner.dname_hpc_logs

    # check that logs directory is created
    assert not (dpath_logs).exists()
    runner._submit_hpc_job([("P1", "1")])
    assert dpath_logs.exists()


def test_submit_hpc_job_no_jobs(
    runner: ProcessingRunner, mocker: pytest_mock.MockFixture
):
    mocked = _set_up_hpc_for_testing(runner, mocker)
    runner._submit_hpc_job([])
    assert not mocked.called


@pytest.mark.parametrize("hpc_type", ["slurm", "sge"])
def test_submit_hpc_job_pysqa_call(
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
    hpc_type,
):
    preamble_list = ["module load some module"]
    hpc_config = {
        "CORES": "8",
        "MEMORY": "32G",
    }

    mocked_submit_job = _set_up_hpc_for_testing(runner, mocker)
    runner.hpc = hpc_type

    runner.hpc_config = HpcConfig(**hpc_config)
    runner.study.config.HPC_PREAMBLE = preamble_list

    participant_ids = ["participant1", "participant2"]
    session_ids = ["session1", "session2"]
    participants_sessions = list(zip(participant_ids, session_ids))

    # Call the function we're testing
    runner._submit_hpc_job(participants_sessions)

    # Extract the arguments passed to submit_job
    submit_job_args = mocked_submit_job.call_args[1]

    # Verify args
    assert submit_job_args["queue"] == hpc_type
    assert submit_job_args["working_directory"] == str(runner.dpath_pipeline_work)
    assert submit_job_args["NIPOPPY_HPC"] == hpc_type
    assert submit_job_args["NIPOPPY_JOB_NAME"] == get_pipeline_tag(
        runner.pipeline_name,
        runner.pipeline_version,
        runner.pipeline_step,
        runner.participant_id,
        runner.session_id,
    )
    assert (
        submit_job_args["NIPOPPY_DPATH_LOGS"]
        == runner.study.layout.dpath_logs / runner.dname_hpc_logs
    )
    assert submit_job_args["NIPOPPY_HPC_PREAMBLE_STRINGS"] == preamble_list

    assert submit_job_args["NIPOPPY_DPATH_ROOT"] == runner.study.layout.dpath_root
    assert submit_job_args["NIPOPPY_PIPELINE_NAME"] == runner.pipeline_name
    assert submit_job_args["NIPOPPY_PIPELINE_VERSION"] == runner.pipeline_version
    assert submit_job_args["NIPOPPY_PIPELINE_STEP"] == runner.pipeline_step

    submitted_participant_ids = submit_job_args["NIPOPPY_PARTICIPANT_IDS"]
    submitted_session_ids = submit_job_args["NIPOPPY_SESSION_IDS"]
    assert submitted_participant_ids == participant_ids
    assert submitted_session_ids == session_ids

    command_list = submit_job_args["NIPOPPY_COMMANDS"]
    assert len(command_list) == len(participants_sessions)
    for participant_id, session_id in participants_sessions:
        assert (f"echo '{participant_id}, {session_id}'") in command_list

    for key, value in hpc_config.items():
        assert submit_job_args.get(key) == value

    template_ast = Environment().parse(FPATH_HPC_TEMPLATE.read_text())
    template_vars = meta.find_undeclared_variables(template_ast)
    nipoppy_args = [arg for arg in submit_job_args.keys() if arg.startswith("NIPOPPY_")]
    for arg in nipoppy_args:
        assert arg in template_vars, f"Variable {arg} not found in the template"

    assert runner.n_success == 2
    assert runner.n_total == 2


@pytest.mark.parametrize(
    "write_job_script,expected_message",
    [(True, "Job script created at "), (False, "No job script found at ")],
)
@pytest.mark.no_xdist
def test_submit_hpc_job_job_script(
    write_job_script: bool,
    expected_message,
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    def touch_job_script(*args, **kwargs):
        fpath_script = runner.dpath_pipeline_work / "run_queue.sh"
        fpath_script.parent.mkdir(parents=True, exist_ok=True)
        fpath_script.touch()

    mocked = _set_up_hpc_for_testing(runner, mocker)
    if write_job_script:
        mocked.side_effect = touch_job_script

    runner._submit_hpc_job([("P1", "1")])
    assert expected_message in caplog.text


def test_submit_hpc_job_pysqa_error(
    runner: ProcessingRunner, mocker: pytest_mock.MockFixture
):
    def write_error_file(*args, **kwargs):
        fpath_error = runner.dpath_pipeline_work / runner.fname_hpc_error
        fpath_error.parent.mkdir(parents=True, exist_ok=True)
        fpath_error.write_text("PYSQA ERROR\n")

    mocked = _set_up_hpc_for_testing(runner, mocker)
    mocked.side_effect = write_error_file
    with pytest.raises(
        RuntimeError, match="Error occurred while submitting the HPC job:\nPYSQA ERROR"
    ):
        runner._submit_hpc_job([("P1", "1")])


@pytest.mark.parametrize("job_id", ["12345", None])
@pytest.mark.no_xdist
def test_submit_hpc_job_job_id(
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
    job_id,
):
    mocked = _set_up_hpc_for_testing(runner, mocker)
    mocked.return_value = job_id
    runner._submit_hpc_job([("P1", "1")])

    if job_id is not None:
        assert f"HPC job ID: {job_id}" in caplog.text
    else:
        assert "HPC job ID" not in caplog.text


def test_run_main_hpc(mocker: pytest_mock.MockFixture, runner: ProcessingRunner):
    # Mock the _submit_hpc_job method
    mocker.patch("os.makedirs", mocker.MagicMock())
    mocked_submit_hpc_job = mocker.patch.object(runner, "_submit_hpc_job")

    # Set the hpc attribute to "exists" to simulate that the HPC is available
    runner.hpc = "exists"

    # Create test manifest and BIDS data
    participants_and_sessions = {"01": ["1", "2", "3"], "02": ["1"]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=runner.study.layout.dpath_bids,
    )
    manifest.save_with_backup(runner.study.layout.fpath_manifest)

    # Call the run_main method
    runner.run_main()

    # Assert that the _submit_hpc_job method was called
    mocked_submit_hpc_job.assert_called_once()

    # Check "participants_sessions" positional argument
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
    extra_flags: Optional[list[str]],
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
