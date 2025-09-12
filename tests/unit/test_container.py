"""Tests for container option handlers."""

import logging
import shlex
from pathlib import Path
from typing import Type

import pytest
import pytest_mock

from nipoppy.container import (
    ApptainerOptionsHandler,
    ContainerOptionsHandler,
    DockerOptionsHandler,
    SingularityOptionsHandler,
)


class _TestOptionsHandler(ContainerOptionsHandler):
    """Class name starts with underscore to avoid Pytest collection."""

    command = "test"
    bind_flag = "-B"


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
