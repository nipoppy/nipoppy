"""Unit tests for Boutiques runner functions."""

import json
import subprocess

import pytest
import pytest_mock

from nipoppy.exceptions import ExecutionError
from nipoppy.workflows.services.boutiques import run_bosh_launch, run_bosh_simulate


@pytest.fixture
def bosh_descriptor():
    """Fixture for a Boutiques descriptor."""
    return {
        "name": "test_app",
        "tool-version": "1.0",
        "command-line": "test_app [INPUT]",
        "inputs": [
            {
                "id": "input_file",
                "name": "Input File",
                "type": "File",
                "value-key": "[INPUT]",
            }
        ],
    }


@pytest.fixture
def invocation():
    """Fixture for a Boutiques invocation."""
    return {"input_file": "/path/to/input.txt"}


@pytest.mark.parametrize(
    "bosh_func,subcommand",
    [
        (run_bosh_launch, "launch"),
        (run_bosh_simulate, "simulate"),
    ],
)
def test_run_bosh_launch(
    bosh_func,
    subcommand,
    bosh_descriptor,
    invocation,
    mocker: pytest_mock.MockerFixture,
):
    """Test that a Boutiques launch or simulate command can be executed."""
    mock_run_command = mocker.Mock()

    exit_code = bosh_func(
        invocation_str=json.dumps(invocation),
        descriptor_str=json.dumps(bosh_descriptor),
        run_command=mock_run_command,
    )

    assert exit_code == 0
    mock_run_command.assert_called_once()
    args, _ = mock_run_command.call_args
    command = args[0]
    assert subcommand in command


@pytest.mark.parametrize(
    "bosh_func,error_msg",
    [
        (run_bosh_launch, "Pipeline execution failed"),
        (run_bosh_simulate, "Pipeline simulation failed"),
    ],
)
def test_bosh_launch_capture_error(
    bosh_func,
    error_msg,
    bosh_descriptor,
    invocation,
    mocker: pytest_mock.MockerFixture,
):
    """Test that a Boutiques launch command captures errors correctly."""
    mock_run_command = mocker.patch(
        "nipoppy.workflows.services.boutiques._run_command",
        side_effect=subprocess.CalledProcessError(
            returncode=1,
            cmd=["bosh", "exec", "launch"],
        ),
    )

    with pytest.raises(ExecutionError, match=error_msg):
        bosh_func(
            invocation_str=json.dumps(invocation),
            descriptor_str=json.dumps(bosh_descriptor),
        )

    mock_run_command.assert_called_once()


def test_bosh_simulate_log(
    bosh_descriptor,
    invocation,
    caplog: pytest.LogCaptureFixture,
    mocker: pytest_mock.MockerFixture,
):
    """Test that a Boutiques simulate command logs the command."""
    mocker.patch("nipoppy.workflows.services.boutiques._run_command")
    run_bosh_simulate(
        invocation_str=json.dumps(invocation),
        descriptor_str=json.dumps(bosh_descriptor),
    )
    assert "Additional launch options:" in caplog.text
