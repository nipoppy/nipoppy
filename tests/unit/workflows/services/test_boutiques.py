"""Unit tests for BoshRunner."""

import pytest

from nipoppy.workflows.services.boutiques import BoshRunner, BoshSimulate


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


def test_bosh_runner_initialization(study, bosh_descriptor):
    """Test that boshRunner can be initialized."""
    runner = BoshRunner(context=study, descriptor=bosh_descriptor)
    assert runner.context is study
    assert runner.descriptor is bosh_descriptor


def test_bosh_runner_run(study, bosh_descriptor, mocker):
    """Test that boshRunner can execute a bosh."""
    import json

    runner = BoshRunner(context=study, descriptor=bosh_descriptor)
    invocation = {"input_file": "/path/to/input.txt"}

    mock_run_command = mocker.Mock()

    exit_code = runner.run(
        invocation_str=json.dumps(invocation),
        descriptor_str=json.dumps(bosh_descriptor),
        run_command=mock_run_command,
    )

    assert exit_code == 0
    mock_run_command.assert_called_once()
    args, _ = mock_run_command.call_args
    command = args[0]
    assert "launch" in command


def test_bosh_simulate_initialization(study, bosh_descriptor):
    """Test that BoshSimulate can be initialized."""
    runner = BoshSimulate(context=study, descriptor=bosh_descriptor)
    assert runner.context is study
    assert runner.descriptor is bosh_descriptor
    assert runner.mode == "Simulating"


def test_bosh_simulate_run(study, bosh_descriptor, mocker):
    """Test that BoshSimulate can execute a bosh simulate command."""
    import json

    runner = BoshSimulate(context=study, descriptor=bosh_descriptor)
    invocation = {"input_file": "/path/to/input.txt"}

    mock_run_command = mocker.Mock()

    exit_code = runner.run(
        invocation_str=json.dumps(invocation),
        descriptor_str=json.dumps(bosh_descriptor),
        run_command=mock_run_command,
    )

    assert exit_code == 0
    mock_run_command.assert_called_once()
    args, _ = mock_run_command.call_args
    command = args[0]
    assert "simulate" in command
