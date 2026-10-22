"""TODO."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.workflows.base import BaseWorkflow


class CohortBuilder:
    """Build a cohort of participant-session pairs from the current filesystem state."""

    def __init__(
        self,
        manifest: Manifest,
        curation_status: CurationStatusTable,
        processing_status: ProcessingStatusTable,
    ):
        self._manifest = manifest
        self._curation_status = curation_status
        self._processing_status = processing_status

    def get_participant_session_pairs(self) -> Iterable[WorkItem]: ...


####


@dataclass(frozen=True)
class WorkItem:
    participant_id: str
    session_id: str


# TODO might want to change the name. Executor is a bit to generic.
T = type[Any]


class Executor(ABC):
    def __init__(self, items: Iterable[WorkItem], command: T):
        self._items = items
        self._command = command

    # TODO: return tuple[list[WorkItem], list[WorkItem]] -> (Success list, Failure list)
    @abstractmethod
    def execute(self): ...


class HPCExecutor(Executor):
    # Mabe could leverage the HPCRunner class nipoppy.workflows.hpcrunner.HPCRunner
    def __init__(self, hpc_config: str):
        self._hpc_config = hpc_config

    def execute(self): ...


class LocalExecutor(Executor):
    def __init__(self, n_jobs: int):
        if n_jobs < 1:
            raise ValueError(f"{n_jobs=} must be a positive integer.")
        self.n_jobs = n_jobs

    def execute(self): ...


####


class ProcessWorkflow(BaseWorkflow):
    def __init__(
        self,
        executor: Executor,
        cohort_builder: CohortBuilder,
    ):
        self._executor = executor
        self._cohort_builder = cohort_builder

    def main(self):
        items = self._cohort_builder.get_participant_session_pairs()
        self._executor.execute(items)
