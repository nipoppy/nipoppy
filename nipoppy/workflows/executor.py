"""TODO."""

from abc import ABC, abstractmethod
from collections import namedtuple
from collections.abc import Iterable

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable

WorkItem = namedtuple("WorkItem", ["participant_id", "session_id"])


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


class Executor(ABC):
    """Abstract base class for executors."""

    @abstractmethod
    def execute(self) -> tuple[list[WorkItem], list[WorkItem]]: ...


class HPCExecutor(Executor):
    # Maybe could leverage the HPCRunner class nipoppy.workflows.hpcrunner.HPCRunner
    def __init__(self, hpc_config: str):
        self._hpc_config = hpc_config

    def execute(self): ...
