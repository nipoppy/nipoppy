"""Base Executor class."""

from abc import ABC, abstractmethod
from collections import namedtuple
from collections.abc import Iterable

from nipoppy.exceptions import ReturnCode

WorkItem = namedtuple("WorkItem", ["participant_id", "session_id"])


class Executor(ABC):
    """Abstract base class for executors."""

    @abstractmethod
    def execute(
        self, items: Iterable[WorkItem]
    ) -> tuple[ReturnCode, list[WorkItem], list[WorkItem]]:
        """Execute a list of work items."""
        raise NotImplementedError()
