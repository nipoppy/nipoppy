"""Tests for the Runner class."""

import copy
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.container import (
    ApptainerHandler,
    ContainerHandler,
    DockerHandler,
    SingularityHandler,
)
from nipoppy.env import ContainerCommandEnum
from nipoppy.exceptions import ConfigError
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.workflows.runner import Runner


def test_run_setup_validates_pipeline_bundle(
    runner: Runner, mocker: pytest_mock.MockFixture
):
    runner.pipeline_version = None
    mocked_check_pipeline_bundle = mocker.patch(
        "nipoppy.workflows.runner.check_pipeline_bundle",
        wraps=check_pipeline_bundle,
    )

    runner.run_setup()

    assert runner.pipeline_version == "1.0.0"
    mocked_check_pipeline_bundle.assert_called_once_with(
        runner.dpath_pipeline_bundle, strict=False
    )


def test_run_validation_error_prevents_execution(
    runner: Runner, mocker: pytest_mock.MockFixture
):
    error = ConfigError("Invalid pipeline bundle")
    mocker.patch(
        "nipoppy.workflows.runner.check_pipeline_bundle",
        side_effect=error,
    )
    mocked_run_main = mocker.patch.object(runner, "run_main")

    with pytest.raises(ConfigError, match="Invalid pipeline bundle"):
        runner.run()

    mocked_run_main.assert_not_called()


@pytest.mark.parametrize(
    "uri,expected_image,expected_type",
    [
        ("docker://owner/project:1.0.0", "owner/project:1.0.0", "docker"),
        (
            "docker://ghcr.io/owner/project:1.0.0",
            "ghcr.io/owner/project:1.0.0",
            "docker",
        ),
        ("shub://owner/project:1.0.0", "owner/project:1.0.0", "singularity"),
        ("library://owner/project:1.0.0", "owner/project:1.0.0", "singularity"),
    ],
)
def test_inject_container_image(
    runner: Runner,
    uri: str,
    expected_image: str,
    expected_type: str,
):
    descriptor = runner._inject_container_image(descriptor=runner.descriptor, uri=uri)
    assert "container-image" in descriptor
    assert descriptor["container-image"]["image"] == expected_image
    assert descriptor["container-image"]["type"] == expected_type


def test_inject_container_image_invalid_uri(
    runner: Runner,
    caplog: pytest.LogCaptureFixture,
):
    runner._inject_container_image(descriptor=runner.descriptor, uri="invalid_uri")
    assert "Failed to parse CONTAINER_INFO.URI" in caplog.text


@pytest.mark.parametrize("simulate", [True, False])
def test_launch_boutiques_run(
    simulate, runner: Runner, mocker: pytest_mock.MockFixture
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
                "--force-apptainer",
                "--no-automounts",
                "--imagepath",
                "--container-opts=",
            ],
        ),
        (
            SingularityHandler(),
            [
                "--force-singularity",
                "--no-automounts",
                "--imagepath",
                "--container-opts=",
            ],
        ),
        (
            DockerHandler(),
            [
                "--force-docker",
                "--no-automounts",
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
    runner: Runner,
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
            assert opt in bosh_command_args, (
                f"Expected container option '{opt}' not found in {bosh_command_args}"
            )

        assert ("--debug" in bosh_command_args) == verbose

    else:
        assert "Additional launch options:" in caplog.text
        assert ("--debug" in caplog.text) == verbose


def test_launch_boutiques_run_bosh_no_container_image(
    runner: Runner,
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
    runner: Runner,
    mocker: pytest_mock.MockFixture,
):
    # remove [[NIPOPPY_DPATH_BIDS]]
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"

    del runner.descriptor["container-image"]

    original_descriptor = copy.deepcopy(runner.descriptor)

    mocked_inject_container_image = mocker.patch.object(
        runner, "_inject_container_image", wraps=runner._inject_container_image
    )

    runner.launch_boutiques_run(participant_id="01", session_id="BL")

    mocked_inject_container_image.assert_called_with(
        original_descriptor,
        runner.pipeline_config.CONTAINER_INFO.URI,
    )


def test_launch_boutiques_run_no_container_image(
    runner: Runner,
    mocker: pytest_mock.MockFixture,
):
    # remove [[NIPOPPY_DPATH_BIDS]]
    runner.descriptor["command-line"] = "echo [ARG1] [ARG2]"

    mocked_inject_container_image = mocker.patch.object(
        runner, "_inject_container_image", wraps=runner._inject_container_image
    )

    runner.launch_boutiques_run(participant_id="01", session_id="BL")

    mocked_inject_container_image.assert_not_called()


def test_process_container_config(runner: Runner, tmp_path: Path):
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
    runner: Runner, tmp_path: Path, mocker: pytest_mock.MockFixture
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


def test_process_container_config_no_bindpaths(runner: Runner):
    # smoke test for no bind paths
    runner.process_container_config(participant_id="01", session_id="BL")
