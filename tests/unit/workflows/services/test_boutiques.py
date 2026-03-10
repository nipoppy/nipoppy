"""Unit tests for Boutiques runner functions."""

import pytest

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


def test_run_bosh_launch(bosh_descriptor, mocker):
    """Test that a Boutiques launch command can be executed."""
    import json

    invocation = {"input_file": "/path/to/input.txt"}

    mock_run_command = mocker.Mock()

    exit_code = run_bosh_launch(
        invocation_str=json.dumps(invocation),
        descriptor_str=json.dumps(bosh_descriptor),
        run_command=mock_run_command,
    )

    assert exit_code == 0
    mock_run_command.assert_called_once()
    args, _ = mock_run_command.call_args
    command = args[0]
    assert "launch" in command


def test_run_bosh_simulate(bosh_descriptor, mocker):
    """Test that BoshSimulate can execute a bosh simulate command."""
    import json

    invocation = {"input_file": "/path/to/input.txt"}

    mock_run_command = mocker.Mock()

    exit_code = run_bosh_simulate(
        invocation_str=json.dumps(invocation),
        descriptor_str=json.dumps(bosh_descriptor),
        run_command=mock_run_command,
    )

    assert exit_code == 0
    mock_run_command.assert_called_once()
    args, _ = mock_run_command.call_args
    command = args[0]
    assert "simulate" in command
