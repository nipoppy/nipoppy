"""Unit tests for BoshRunner."""

import pytest

from nipoppy.config.main import Config
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.workflows.services.boutiques import BoshRunner, BoshSimulate
from nipoppy.workflows.services.context import WorkflowContext


@pytest.fixture
def workflow_context(tmp_path):
    """Fixture for WorkflowContext."""
    layout = DatasetLayout(tmp_path)
    logger = get_logger("test_logger")
    config = Config()
    return WorkflowContext(layout=layout, logger=logger, config=config)


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


def test_bosh_runner_initialization(workflow_context, bosh_descriptor):
    """Test that boshRunner can be initialized."""
    runner = BoshRunner(context=workflow_context, descriptor=bosh_descriptor)
    assert runner.context is workflow_context
    assert runner.descriptor is bosh_descriptor


def test_bosh_runner_run(workflow_context, bosh_descriptor, mocker):
    """Test that boshRunner can execute a bosh."""
    import json

    runner = BoshRunner(context=workflow_context, descriptor=bosh_descriptor)
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


def test_bosh_simulate_initialization(workflow_context, bosh_descriptor):
    """Test that BoshSimulate can be initialized."""
    runner = BoshSimulate(context=workflow_context, descriptor=bosh_descriptor)
    assert runner.context is workflow_context
    assert runner.descriptor is bosh_descriptor
    assert runner.mode == "Simulating"


def test_bosh_simulate_run(workflow_context, bosh_descriptor, mocker):
    """Test that BoshSimulate can execute a bosh simulate command."""
    import json

    runner = BoshSimulate(context=workflow_context, descriptor=bosh_descriptor)
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
