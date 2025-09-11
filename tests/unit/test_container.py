"""Tests for container option handlers."""

import pytest
import pytest_mock

from nipoppy.container import ContainerOptionsHandler


class TestOptionsHandler(ContainerOptionsHandler):
    command = "test"
    bind_flag = "--test-bind-flag"


@pytest.fixture
def handler() -> ContainerOptionsHandler:
    return TestOptionsHandler()


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
