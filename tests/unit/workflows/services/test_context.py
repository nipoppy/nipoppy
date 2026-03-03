"""Unit tests for WorkflowContext."""

import pytest

from nipoppy.config.main import Config
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.workflows.services.context import WorkflowContext


def test_workflow_context_initialization(tmp_path):
    """Test that WorkflowContext can be initialized with required attributes."""
    layout = DatasetLayout(tmp_path)
    logger = get_logger("test_logger")
    config = Config()

    context = WorkflowContext(layout=layout, logger=logger, config=config)

    assert context.layout is layout
    assert context.logger is logger
    assert context.config is config


def test_workflow_context_missing_attributes():
    """Test that WorkflowContext raises TypeError if required attributes are missing."""
    with pytest.raises(TypeError):
        WorkflowContext()
