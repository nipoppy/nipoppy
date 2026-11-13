"""Base Executor class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from nipoppy.exceptions import ReturnCode


@dataclass(frozen=True)
class WorkItem:
    """A participant-session pair to execute."""

    participant_id: str | None
    session_id: str | None


ResultT = TypeVar("ResultT")


@dataclass
class ExecutionResult(Generic[ResultT]):
    """Outcome of executing a list of work items."""

    return_code: ReturnCode
    succeeded: list[WorkItem]
    failed: list[WorkItem]
    results: dict[WorkItem, ResultT] = field(default_factory=dict)


class Executor(ABC, Generic[ResultT]):
    """Abstract base class for executors."""

    @abstractmethod
    def execute(self, items: list[WorkItem]) -> ExecutionResult[ResultT]:
        """Execute a list of work items."""
        raise NotImplementedError()
