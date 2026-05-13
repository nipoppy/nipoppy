"""Tests for the Runner class."""

import copy
import json
from pathlib import Path
from typing import Optional

import pytest
import pytest_mock
from jinja2 import Environment, meta

from nipoppy.config.hpc import HpcConfig
from nipoppy.container import (
    ApptainerHandler,
    ContainerHandler,
    DockerHandler,
    SingularityHandler,
)
from nipoppy.env import ContainerCommandEnum
from nipoppy.exceptions import WorkflowError
from nipoppy.layout import LayoutError
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


@pytest.mark.parametrize(
    "uri,expected_image,expected_type",
    [
        ("docker://owner/project:1.0.0", "owner/project:1.0.0", "docker"),
        ("shub://owner/project:1.0.0", "owner/project:1.0.0", "singularity"),
        ("library://owner/project:1.0.0", "owner/project:1.0.0", "singularity"),
    ],
)
def test_set_container_image(
    runner: ProcessingRunner,
    uri: str,
    expected_image: str,
    expected_type: str,
):
    descriptor = runner._set_container_image(descriptor=runner.descriptor, uri=uri)
    assert "container-image" in descriptor
    assert descriptor["container-image"]["image"] == expected_image
    assert descriptor["container-image"]["type"] == expected_type


def test_set_container_image_invalid_uri(
    runner: ProcessingRunner,
    caplog: pytest.LogCaptureFixture,
):
    runner._set_container_image(descriptor=runner.descriptor, uri="invalid_uri")
    assert "Failed to parse CONTAINER_INFO.URI" in caplog.text


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
    runner.pipeline_config.CONTAINER_INFO.URI = None

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


def test_launch_boutiques_run_container_image(
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
):
    participant_id = "01"
    session_id = "BL"

    # remove [[NIPOPPY_DPATH_BIDS]]
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"

    del runner.descriptor["container-image"]

    original_descriptor = copy.deepcopy(runner.descriptor)

    mocked_set_container_image = mocker.patch.object(
        runner, "_set_container_image", wraps=runner._set_container_image
    )

    runner.launch_boutiques_run(
        participant_id,
        session_id,
    )

    mocked_set_container_image.assert_called_with(
        original_descriptor,
        runner.pipeline_config.CONTAINER_INFO.URI,
    )


def test_launch_boutiques_run_no_container_image(
    runner: ProcessingRunner,
    mocker: pytest_mock.MockFixture,
):
    participant_id = "01"
    session_id = "BL"

    # remove [[NIPOPPY_DPATH_BIDS]]
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"

    mocked_set_container_image = mocker.patch.object(
        runner, "_set_container_image", wraps=runner._set_container_image
    )

    runner.launch_boutiques_run(
        participant_id,
        session_id,
    )

    mocked_set_container_image.assert_not_called()


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
