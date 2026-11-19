"""Base Executor class."""

from abc import ABC, abstractmethod
from collections import namedtuple
from collections.abc import Sequence
from dataclasses import dataclass

from nipoppy.exceptions import ReturnCode

WorkItem = namedtuple("WorkItem", ["participant_id", "session_id"])


@dataclass(frozen=True)
class ExecutorResult:
    """Result of an execution."""

    return_code: ReturnCode


class Executor(ABC):
    """Abstract base class for executors."""

    @abstractmethod
    def execute(self, items: Sequence[WorkItem]) -> ExecutorResult:
        """Execute a list of work items."""
        raise NotImplementedError()
