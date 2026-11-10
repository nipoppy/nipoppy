"""Local executor with multiprocessing support."""

from collections.abc import Callable, Iterable
from typing import Any

import rich

from nipoppy.console import _INDENT, CONSOLE_STDOUT
from nipoppy.exceptions import ExecutionError, InvalidArgumentError, ReturnCode
from nipoppy.logger import get_logger
from nipoppy.workflows.executor import Executor, WorkItem

try:
    from joblib import Parallel, delayed

    JOBLIB_INSTALLED = True

except ImportError as error:
    if str(error).startswith("No module named 'joblib'"):
        JOBLIB_INSTALLED = False
    else:
        raise

logger = get_logger()


def _get_return_code(n_success: int, n_total: int) -> ReturnCode:
    if n_total == 0:
        return ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN
    elif n_success == 0:
        return ReturnCode.FAILURE
    elif n_success < n_total:
        return ReturnCode.PARTIAL_SUCCESS
    else:
        return ReturnCode.SUCCESS


def _log_summary_message(n_success, n_total, is_study_level=False):
    if n_total == 0:
        logger.warning(
            "No participants or sessions to run. Make sure there are no mistakes "
            "in the input arguments, the dataset's manifest or config file, or "
            "the curation status file"
        )
    else:
        if is_study_level:
            log_msg = "Ran on the entire study"
        else:
            log_msg = (
                f"Ran for {n_success} out of {n_total} participants and/or sessions"
            )

        if n_success == 0:
            logger.error(log_msg)
        elif n_success == n_total:
            logger.success(log_msg)
        else:
            logger.warning(log_msg)


class LocalExecutor(Executor):
    def __init__(
        self,
        work_fn: Callable[[WorkItem], Any],
        error_message_builder: Callable[[WorkItem], str],
        n_jobs: int = 1,
        show_progress: bool = False,
        progress_bar_description: str = "Working...",  # default used by rich
    ):
        super().__init__()

        self.work_fn = work_fn
        self.n_jobs = n_jobs
        self.error_message_builder = error_message_builder
        self.show_progress = show_progress
        self.progress_bar_description = progress_bar_description
        self.results: list[Any] | None = None

        self._check_args()

    def _check_args(self):

        if self.n_jobs < 1:
            raise InvalidArgumentError(
                f"{self.n_jobs=} must be a positive integer or None."
            )

        if not JOBLIB_INSTALLED and self.n_jobs != 1:
            raise ExecutionError(
                "An additional dependency is required to enable local parallelization "
                "with --n-jobs. Install it with: pip install nipoppy[parallel]",
                hint=None,
            )

    def execute(
        self, items: Iterable[WorkItem]
    ) -> tuple[list[WorkItem], list[WorkItem]]:
        """Run pipeline locally and collect results."""
        self.results = []
        successful_items = []
        failed_items = []
        n_success = 0
        n_total = 0
        for (status, result), item in zip(self._get_statuses_and_results(items), items):
            if status is True:
                successful_items.append(item)
                n_success += 1
            else:
                failed_items.append(item)
            n_total += 1
            self.results.append(result)

        _log_summary_message(
            n_success,
            n_total,
            is_study_level=(items == [WorkItem(participant_id=None, session_id=None)]),
        )

        return _get_return_code(n_success, n_total), successful_items, failed_items

    def _work_fn_wrapper(self, item: WorkItem) -> bool:
        """
        Run a single participant/session and handle exceptions.

        This is a helper function for parallelization with joblib.
        Returns (True, <result>) if the run was successful, (False, None) otherwise.
        """
        try:
            # success
            return True, self.work_fn(*item)
        except Exception as exception:
            logger.error(f"{self.error_message_builder(item)}: {exception}")

        # failure
        return False, None

    def _get_statuses_and_results(
        self, work_items: Iterable[WorkItem]
    ) -> list[tuple[bool, Any]]:
        work_items = list(work_items)
        n_total = len(work_items)
        if JOBLIB_INSTALLED:
            wrapper_func = delayed(self._work_fn_wrapper)
        else:
            wrapper_func = self._work_fn_wrapper

        results_generator = (wrapper_func(work_item) for work_item in work_items)

        if JOBLIB_INSTALLED:
            results_generator = Parallel(
                n_jobs=self.n_jobs,
                backend="threading",
                return_as="generator",
            )(results_generator)

        if self.show_progress and n_total != 0:
            results_generator = rich.progress.track(
                results_generator,
                description=f"{' ' * _INDENT}{self.progress_bar_description}",
                total=n_total,
                console=CONSOLE_STDOUT,
            )

        return list(results_generator)
