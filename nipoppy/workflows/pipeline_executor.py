"""Execution loop functionality for pipeline workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable, Optional, Tuple

import rich.progress

from nipoppy.console import _INDENT, CONSOLE_STDOUT

if TYPE_CHECKING:
    from nipoppy.logger import NipoppyLogger

try:
    from joblib import Parallel, delayed

    JOBLIB_INSTALLED = True

except ImportError as error:
    if str(error).startswith("No module named 'joblib'"):
        JOBLIB_INSTALLED = False
    else:
        raise


class PipelineExecutor:
    """Handles execution loop and parallelization for pipeline workflows."""

    def __init__(
        self,
        logger: NipoppyLogger,
        pipeline_name: str,
        pipeline_version: str,
        n_jobs: int = 1,
        show_progress: bool = False,
        progress_bar_description: str = "Working...",
    ):
        """Initialize the pipeline executor.

        Parameters
        ----------
        logger : NipoppyLogger
            Logger instance
        pipeline_name : str
            Name of the pipeline
        pipeline_version : str
            Version of the pipeline
        n_jobs : int
            Number of parallel jobs
        show_progress : bool
            Whether to show progress bar
        progress_bar_description : str
            Description for progress bar
        """
        self.logger = logger
        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version
        self.n_jobs = n_jobs
        self.show_progress = show_progress
        self.progress_bar_description = progress_bar_description

    def run_single_wrapper(
        self,
        run_single_func: Callable,
        participant_id: str,
        session_id: str,
    ) -> Tuple[bool, any]:
        """
        Run a single participant/session and handle exceptions.

        This is a helper function for parallelization with joblib.
        Returns (True, <result>) if the run was successful, (False, None) otherwise.

        Parameters
        ----------
        run_single_func : Callable
            Function to run for a single participant/session
            Should accept (participant_id, session_id) and return result
        participant_id : str
            Participant ID
        session_id : str
            Session ID

        Returns
        -------
        Tuple[bool, any]
            (success status, result or None)
        """
        try:
            # success
            return True, run_single_func(participant_id, session_id)
        except Exception as exception:
            self.logger.error(
                f"Error running {self.pipeline_name} {self.pipeline_version}"
                f" on participant {participant_id}, session {session_id}"
                f": {exception}"
            )

        # failure
        return False, None

    def get_results_generator(
        self,
        run_single_func: Callable,
        participants_sessions: Iterable[Tuple[str, str]],
    ):
        """Create a generator for execution results.

        Parameters
        ----------
        run_single_func : Callable
            Function to run for a single participant/session
        participants_sessions : Iterable[Tuple[str, str]]
            Participant-session pairs to process

        Returns
        -------
        Generator
            Generator yielding (success_status, result) tuples
        """
        participants_sessions = list(participants_sessions)
        n_total = len(participants_sessions)

        if JOBLIB_INSTALLED:
            wrapper_func = delayed(
                lambda p, s: self.run_single_wrapper(run_single_func, p, s)
            )
        else:
            wrapper_func = lambda p, s: self.run_single_wrapper(
                run_single_func, p, s
            )

        results_generator = (
            wrapper_func(participant_id, session_id)
            for participant_id, session_id in participants_sessions
        )

        if JOBLIB_INSTALLED and self.n_jobs != 1:
            results_generator = Parallel(
                n_jobs=self.n_jobs,
                backend="threading",
                return_as="generator",
            )(results_generator)

        if self.show_progress and n_total != 0:
            results_generator = rich.progress.track(
                results_generator,
                description=f'{" "*_INDENT}{self.progress_bar_description}',
                total=n_total,
                console=CONSOLE_STDOUT,
            )

        return results_generator

    def execute_participants_sessions(
        self,
        run_single_func: Callable,
        participants_sessions: Iterable[Tuple[str, str]],
    ) -> Tuple[int, int, list]:
        """Execute pipeline for all participant-session pairs.

        Parameters
        ----------
        run_single_func : Callable
            Function to run for a single participant/session
        participants_sessions : Iterable[Tuple[str, str]]
            Participant-session pairs to process

        Returns
        -------
        Tuple[int, int, list]
            (n_success, n_total, run_single_results)
        """
        results = list(self.get_results_generator(run_single_func, participants_sessions))

        if len(results) == 0:
            return 0, 0, []

        run_statuses, run_single_results = zip(*results)
        n_success = sum(run_statuses)
        n_total = len(run_statuses)

        return n_success, n_total, list(run_single_results)
