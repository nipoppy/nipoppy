"""Tests for container option handlers."""

import logging
import shlex
from pathlib import Path
from typing import Type

import pytest
import pytest_mock

from nipoppy.config.container import ContainerConfig
from nipoppy.container import (
    ApptainerOptionsHandler,
    ContainerOptionsHandler,
    DockerOptionsHandler,
    SingularityOptionsHandler,
    get_container_options_handler,
)


class _TestOptionsHandler(ContainerOptionsHandler):
    """Class name starts with underscore to avoid Pytest collection."""

    command = "test"
    bind_flag = "-B"

    def is_image_downloaded(self, uri, fpath_container):
        return True

    def get_container_pull_command(self, uri, fpath_container):
        return "not_used"


@pytest.fixture
def handler() -> ContainerOptionsHandler:
    return _TestOptionsHandler()


@pytest.mark.parametrize(
    "subclass",
    [ApptainerOptionsHandler, SingularityOptionsHandler, DockerOptionsHandler],
)
def test_subclass(subclass: Type[ContainerOptionsHandler]):
    # try to instantiate subclass
    handler = subclass()
    assert isinstance(handler, ContainerOptionsHandler)


@pytest.mark.parametrize(
    "args,expected_args", [(None, []), (["--some-arg"], ["--some-arg"])]
)
def test_init_args(args, expected_args):
    handler = _TestOptionsHandler(args=args)
    assert handler.args == expected_args


@pytest.mark.parametrize("logger", [None, logging.getLogger("test_logger")])
def test_init_logger(logger):
    handler = _TestOptionsHandler(logger=logger)
    assert isinstance(handler.logger, logging.Logger)


def test_check_container_command(
    handler: ContainerOptionsHandler, mocker: pytest_mock.MockerFixture
):
    # should not raise error
    mocked_which = mocker.patch(
        "nipoppy.container.shutil.which", return_value="/some/path/to/command"
    )
    handler.check_container_command()
    mocked_which.assert_called_once_with(handler.command)


def test_check_container_command_error(
    handler: ContainerOptionsHandler, mocker: pytest_mock.MockerFixture
):
    mocker.patch("nipoppy.container.shutil.which", return_value=None)
    with pytest.raises(RuntimeError, match="Container executable not found"):
        handler.check_container_command()


@pytest.mark.parametrize(
    "args,path_local,path_inside_container,mode,expected",
    [
        (
            [],
            "/my/local/path",
            "my/container/path",
            "ro",
            ["-B", "/my/local/path:my/container/path:ro"],
        ),
        (
            ["other_arg"],
            "/my/local/path",
            None,
            "ro",
            ["other_arg", "-B", "/my/local/path"],
        ),
        (
            [],
            "relative_path",
            None,
            "rw",
            [
                "-B",
                f"{Path('relative_path').resolve()}",
            ],
        ),
    ],
)
def test_add_bind_path(
    handler: ContainerOptionsHandler,
    args,
    path_local,
    path_inside_container,
    mode,
    expected,
):
    handler.args = args

    handler.add_bind_path(
        path_local=path_local,
        path_inside_container=path_inside_container,
        mode=mode,
    )
    assert handler.args == expected


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--cleanenv"],
        ["--cleanenv", "-B", "/"],
        ["-B", "/", "-B", "/:relative_path_in_container", "-B", "/:/:ro"],
    ],
)
def test_check_container_args(args, handler: ContainerOptionsHandler, caplog):
    handler.args = args
    handler.check_container_args()

    # no change to arguments
    assert handler.args == args


def test_check_container_args_relative(
    handler: ContainerOptionsHandler, caplog: pytest.LogCaptureFixture
):
    handler.args = ["-B", "."]
    caplog.set_level(logging.DEBUG, logger=handler.logger.name)

    handler.check_container_args()

    assert handler.args == ["-B", str(Path(".").resolve())]
    assert "Resolving path" in caplog.text


def test_check_container_args_symlink(
    handler: ContainerOptionsHandler, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    path_symlink = tmp_path / "symlink"
    path_real = tmp_path / "file.txt"
    path_real.touch()
    path_symlink.symlink_to(path_real)

    handler.args = ["-B", str(path_symlink)]
    caplog.set_level(logging.DEBUG, logger=handler.logger.name)

    handler.check_container_args()

    assert handler.args == ["-B", str(path_real)]
    assert "Resolving path" in caplog.text


def test_check_container_args_missing(
    handler: ContainerOptionsHandler, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    dpath = tmp_path / "missing"
    assert not dpath.exists()

    handler.args = ["-B", str(dpath)]
    caplog.set_level(logging.DEBUG, logger=handler.logger.name)

    handler.check_container_args()

    assert dpath.exists()
    assert "Creating missing directory" in caplog.text


def test_check_container_args_error(handler: ContainerOptionsHandler):
    handler.args = ["-B"]
    with pytest.raises(RuntimeError, match="Error parsing"):
        handler.check_container_args()


@pytest.mark.parametrize(
    "env_vars",
    [
        {"VAR1": "1"},
        {"VAR2": "test"},
        {"VAR3": "123", "VAR4": ""},
    ],
)
def test_set_container_env_vars(handler: ContainerOptionsHandler, env_vars: dict):
    handler.set_container_env_vars(env_vars)
    args_str = shlex.join(handler.args)
    for key, value in env_vars.items():
        assert f"{handler.env_flag} {key}={value}" in args_str


@pytest.mark.parametrize(
    "handler,subcommand,expected",
    [
        (
            ApptainerOptionsHandler(args=["--env", "VAR1=1"]),
            "run",
            "apptainer run --env VAR1=1",
        ),
        (
            SingularityOptionsHandler(args=["--cleanenv"]),
            "exec",
            "singularity exec --cleanenv",
        ),
        (
            DockerOptionsHandler(
                args=["--volume", ".:/container/path:ro", "--env", "VAR2=value"]
            ),
            "run",
            f"docker run --volume {Path('.').resolve()}:/container/path:ro --env VAR2=value",  # noqa: E501
        ),
    ],
)
def test_prepare_container(
    handler: ContainerOptionsHandler,
    subcommand: str,
    expected: str,
    mocker: pytest_mock.MockerFixture,
):
    # pretend command exists
    mocked_check_container_command = mocker.patch.object(
        handler, "check_container_command", return_value=handler.command
    )
    assert handler.prepare_container(subcommand=subcommand) == expected
    mocked_check_container_command.assert_called_once()


@pytest.mark.parametrize(
    "config,expected",
    [
        (
            ContainerConfig(
                COMMAND="apptainer",
                ARGS=["--cleanenv", "--bind", "fake_path"],
                ENV_VARS={"VAR1": "1"},
            ),
            ApptainerOptionsHandler(
                args=["--cleanenv", "--bind", "fake_path", "--env", "VAR1=1"],
            ),
        ),
        (
            ContainerConfig(
                COMMAND="singularity",
                ARGS=[],
            ),
            SingularityOptionsHandler(
                args=[],
            ),
        ),
        (
            ContainerConfig(
                COMMAND="docker",
                ARGS=["--volume", "path"],
                ENV_VARS={"VAR3": "123"},
            ),
            DockerOptionsHandler(
                args=["--volume", "path", "--env", "VAR3=123"],
            ),
        ),
    ],
)
def test_get_container_options_handler(
    config: ContainerConfig, expected: ContainerOptionsHandler
):
    handler = get_container_options_handler(config)
    assert isinstance(handler, expected.__class__)
    assert handler.bind_sep == expected.bind_sep
    assert handler.env_flag == expected.env_flag
    assert handler.command == expected.command
    assert handler.bind_flag == expected.bind_flag
    assert handler.env_flag == expected.env_flag
    assert handler.args == expected.args


@pytest.mark.parametrize(
    "uri,fpath_container,exists",
    [
        ("docker://test/test:latest", "exists.sif", True),
        ("docker://test/test:latest", "does_not_exist.sif", False),
    ],
)
@pytest.mark.parametrize(
    "handler", [ApptainerOptionsHandler(), SingularityOptionsHandler()]
)
def test_is_image_downloaded_apptainer_singularity(
    handler: ContainerOptionsHandler,
    uri,
    fpath_container,
    exists,
    mocker: pytest_mock.MockerFixture,
):
    mocker.patch(
        "nipoppy.container.Path.exists",
        autospec=True,
        side_effect=lambda x: True if x.name == "exists.sif" else False,
    )

    assert handler.is_image_downloaded(uri, fpath_container) == exists


@pytest.mark.parametrize(
    "uri,exists",
    [
        ("docker://test/downloaded_image:latest", True),
        ("test/downloaded_image:latest", True),
        ("docker://test/missing_image:latest", False),
        ("missing_image:latest", False),
    ],
)
def test_is_image_downloaded_docker(
    uri,
    exists,
    mocker: pytest_mock.MockerFixture,
):
    handler = DockerOptionsHandler()

    # mock subprocess.run to simulate docker image existing
    def mock_run(cmd, *args, **kwargs):
        class MockCompletedProcess:
            def __init__(self, returncode, stdout):
                self.returncode = returncode
                self.stdout = stdout

        if cmd == ["docker", "image", "inspect", "test/downloaded_image:latest"]:
            return MockCompletedProcess(0, "test/downloaded_image:latest\n")
        else:
            return MockCompletedProcess(1, "")

    mocker.patch("nipoppy.container.subprocess.run", side_effect=mock_run)

    assert handler.is_image_downloaded(uri, "not_used") == exists


@pytest.mark.parametrize(
    "handler,uri,expected_command",
    [
        (
            ApptainerOptionsHandler(),
            "docker://test/test:latest",
            "apptainer pull path/to/container.sif docker://test/test:latest",
        ),
        (
            SingularityOptionsHandler(),
            "docker://test/test:latest",
            "singularity pull path/to/container.sif docker://test/test:latest",
        ),
        (
            DockerOptionsHandler(),
            "docker://test/test:latest",
            "docker pull test/test:latest",
        ),
        (
            DockerOptionsHandler(),
            "test/test:latest",
            "docker pull test/test:latest",
        ),
    ],
)
def test_get_container_pull_command(
    handler: ContainerOptionsHandler, uri, expected_command
):
    fpath_container = "path/to/container.sif"
    assert handler.get_container_pull_command(uri, fpath_container) == expected_command
