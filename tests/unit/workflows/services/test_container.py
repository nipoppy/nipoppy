"""Unit tests for ContainerRunner."""

import pytest

from nipoppy.config.main import Config
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.workflows.services.container import ContainerRunner
from nipoppy.workflows.services.context import WorkflowContext


@pytest.fixture
def workflow_context(tmp_path):
    """Fixture for WorkflowContext."""
    layout = DatasetLayout(tmp_path)
    logger = get_logger("test_logger")
    config = Config()
    return WorkflowContext(layout=layout, logger=logger, config=config)


@pytest.fixture
def container_descriptor():
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


def test_container_runner_initialization(workflow_context, container_descriptor):
    """Test that ContainerRunner can be initialized."""
    runner = ContainerRunner(context=workflow_context, descriptor=container_descriptor)
    assert runner.context is workflow_context
    assert runner.descriptor is container_descriptor


def test_container_runner_run(workflow_context, container_descriptor, mocker):
    """Test that ContainerRunner can execute a container."""
    runner = ContainerRunner(context=workflow_context, descriptor=container_descriptor)
    invocation = {"input_file": "/path/to/input.txt"}

    # Mock the Boutiques execution
    mock_bosh = mocker.patch(
        "nipoppy.workflows.services.container.bosh",
        return_value=mocker.Mock(exit_code=0),
    )

    exit_code = runner.run(invocation)

    assert exit_code == 0
    assert mock_bosh.call_count == 3  # validate, invocation, exec launch
