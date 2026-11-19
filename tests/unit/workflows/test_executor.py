"""Tests for the base Executor class."""

from collections.abc import Sequence

import pytest

from nipoppy.exceptions import InvalidArgumentError, ReturnCode
from nipoppy.workflows.executor import Executor, ExecutorResult, WorkItem


class DummyExecutor(Executor):
    """Minimal concrete executor that succeeds on every item."""

    def _execute(self, items: Sequence[WorkItem]) -> ExecutorResult:
        return ExecutorResult(
            return_code=ReturnCode.SUCCESS,
            successful_items=list(items),
            failed_items=[],
        )


class TestExecute:
    @pytest.mark.parametrize(
        "items",
        [
            [],
            [WorkItem("01", "1")],
            (WorkItem("01", "1"), WorkItem("01", "2")),
            [WorkItem(None, None)],
        ],
    )
    def test_valid_items(self, items):
        """Test that valid items are passed through to _execute."""
        result = DummyExecutor().execute(items)
        assert result.successful_items == list(items)

    @pytest.mark.parametrize(
        "items_type", [iter, lambda items: (item for item in items), set]
    )
    def test_items_is_not_sequence(self, items_type):
        """Test that an error is raised when items is not a Sequence."""
        items = items_type([WorkItem("01", "1"), WorkItem("01", "2")])
        with pytest.raises(
            InvalidArgumentError,
            match="is not an instance of collections.abc.Sequence",
        ):
            DummyExecutor().execute(items)

    @pytest.mark.parametrize(
        "items",
        [
            [("01", "1")],
            [WorkItem("01", "1"), ("01", "2")],
            ["01"],
            "01",
        ],
    )
    def test_item_is_not_work_item(self, items):
        """Test that an error is raised when an item is not a WorkItem."""
        with pytest.raises(
            InvalidArgumentError, match="All items must be instances of WorkItem"
        ):
            DummyExecutor().execute(items)

    def test_no_execution_on_invalid_input(self, mocker):
        """Test that _execute is not called if validation fails."""
        executor = DummyExecutor()
        spy = mocker.spy(executor, "_execute")
        with pytest.raises(InvalidArgumentError):
            executor.execute([("01", "1")])
        spy.assert_not_called()
