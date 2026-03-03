"""Unit tests for TabularDataHandler."""

import pandas as pd
import pytest

from nipoppy.config.main import Config
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.workflows.services.context import WorkflowContext
from nipoppy.workflows.services.tabular import TabularDataHandler


@pytest.fixture
def workflow_context(tmp_path):
    """Fixture for WorkflowContext."""
    layout = DatasetLayout(tmp_path)
    logger = get_logger("test_logger")
    config = Config()
    return WorkflowContext(layout=layout, logger=logger, config=config)


def test_tabular_data_handler_initialization(workflow_context):
    """Test that TabularDataHandler can be initialized."""
    handler = TabularDataHandler(context=workflow_context)
    assert handler.context is workflow_context


def test_tabular_data_handler_load(workflow_context, tmp_path):
    """Test that TabularDataHandler can load a tabular file."""
    handler = TabularDataHandler(context=workflow_context)

    # Create a dummy CSV file
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    file_path = tmp_path / "test.csv"
    df.to_csv(file_path, index=False)

    loaded_df = handler.load(str(file_path))

    pd.testing.assert_frame_equal(loaded_df, df)


def test_tabular_data_handler_save(workflow_context, tmp_path):
    """Test that TabularDataHandler can save a tabular file."""
    handler = TabularDataHandler(context=workflow_context)

    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    file_path = tmp_path / "test_save.csv"

    handler.save(df, str(file_path))

    assert file_path.exists()
    loaded_df = pd.read_csv(file_path)
    pd.testing.assert_frame_equal(loaded_df, df)
