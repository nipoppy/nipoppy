"""Tests for container option handlers."""

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
    bind_flag = "--test-bind-flag"


@pytest.fixture
def handler() -> ContainerOptionsHandler:
    return _TestOptionsHandler()


@pytest.mark.parametrize(
    "subclass",
    [ApptainerOptionsHandler, SingularityOptionsHandler, DockerOptionsHandler],
)
@pytest.mark.parametrize(
    "args,expected_args", [(None, []), ([], []), (["--some-arg"], ["--some-arg"])]
)
def test_init(subclass: Type[ContainerOptionsHandler], args, expected_args):
    # try to instantiate subclass
    handler = subclass(args=args)
    assert isinstance(handler, ContainerOptionsHandler)
    assert handler.args == expected_args


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
