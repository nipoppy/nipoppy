"""Base Executor class."""

from abc import ABC, abstractmethod
from collections import namedtuple
from collections.abc import Sequence
from dataclasses import dataclass
from typing import final

from nipoppy.exceptions import InvalidArgumentError, ReturnCode

WorkItem = namedtuple("WorkItem", ["participant_id", "session_id"])


@dataclass(frozen=True)
class ExecutorResult:
    """Result of an execution."""

    return_code: ReturnCode
    successful_items: list[WorkItem]
    failed_items: list[WorkItem]


class Executor(ABC):
    """Abstract base class for executors."""

    @final
    def execute(self, items: Sequence[WorkItem]) -> ExecutorResult:
        """Validate and execute a sequence of work items."""
        if not isinstance(items, Sequence):
            raise InvalidArgumentError(
                f"{items=} ({type(items)}) is not an instance of collections.abc.Sequence."  # noqa: E501
            )
        invalid_items = [item for item in items if not isinstance(item, WorkItem)]
        if invalid_items:
            raise InvalidArgumentError(
                f"All items must be instances of WorkItem, got: {invalid_items}"
            )
        return self._execute(items)

    @abstractmethod
    def _execute(self, items: Sequence[WorkItem]) -> ExecutorResult:
        """Execute a sequence of validated work items."""
        raise NotImplementedError()
