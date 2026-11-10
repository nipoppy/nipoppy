"""Tests for LocalExecutor."""

import builtins
import importlib
from functools import partial
from typing import Callable

import pytest
import pytest_mock

import nipoppy.workflows._local_executor  # for mocking
from nipoppy.exceptions import ExecutionError, InvalidArgumentError, ReturnCode
from nipoppy.workflows._local_executor import (
    LocalExecutor,
    _get_return_code,
    _log_summary_message,
)
from nipoppy.workflows.executor import WorkItem


def _mock_joblib_import_error(mocker: pytest_mock.MockerFixture, error_message: str):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "joblib":
            raise ImportError(error_message)
        return real_import(name, *args, **kwargs)

    mocker.patch("builtins.__import__", side_effect=fake_import)


@pytest.fixture(scope="function")
def partial_executor() -> Callable[..., LocalExecutor]:

    def work_fn(participant_id: str, session_id: str):
        if participant_id == "FAIL":
            raise RuntimeError("Simulated failure")
        else:
            return "SUCCESS"

    return partial(
        LocalExecutor,
        work_fn=work_fn,
        error_message_builder=lambda x: f"Error for {x.participant_id}, {x.session_id}",
    )


@pytest.fixture(scope="function")
def reimport_joblib(mocker: pytest_mock.MockerFixture):
    """Fixture for tests where joblib import was manipulated."""
    yield

    # fmt: off
    mocker.stopall()
    import nipoppy.workflows._local_executor
    importlib.reload(nipoppy.workflows._local_executor)
    from nipoppy.workflows._local_executor import LocalExecutor  # noqa F401
    from nipoppy.workflows._local_executor import (
        JOBLIB_INSTALLED,
    )
    assert JOBLIB_INSTALLED
    # fmt: on


class TestGetReturnCode:
    @pytest.mark.parametrize(
        ["n_success", "n_total", "expected_return_code"],
        [
            (0, 0, ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN),
            (0, 5, ReturnCode.FAILURE),
            (3, 6, ReturnCode.PARTIAL_SUCCESS),
            (7, 7, ReturnCode.SUCCESS),
        ],
    )
    def test_get_return_code(self, n_success, n_total, expected_return_code):
        """Test that the return code is correct."""
        assert _get_return_code(n_success, n_total) == expected_return_code


class TestLogSummaryMessage:
    @pytest.mark.parametrize(
        ["n_success", "n_total", "is_study_level", "expected_message", "level"],
        [
            (0, 0, False, "No participants or sessions to run", "WARNING"),
            (0, 5, False, "Ran for 0 out of 5 participants and/or sessions", "ERROR"),
            (3, 6, False, "Ran for 3 out of 6 participants and/or sessions", "WARNING"),
            (7, 7, False, "Ran for 7 out of 7 participants and/or sessions", "INFO"),
            (1, 1, True, "Ran on the entire study", "INFO"),
            (0, 1, True, "Ran on the entire study", "ERROR"),
        ],
    )
    def test_log_summary_message(
        self, n_success, n_total, is_study_level, expected_message, level, caplog
    ):
        """Test that the log summary message is correct."""
        _log_summary_message(n_success, n_total, is_study_level)
        assert any(
            expected_message in record.message and record.levelname == level
            for record in caplog.records
        )


class TestJoblibImport:
    def test_import_error_propagates(self, mocker: pytest_mock.MockFixture):
        """Test that ImportError is propagated if joblib exists but import fails."""
        # pretend that joblib is not installed
        error_message = "Unexpected exception during import"
        _mock_joblib_import_error(mocker, error_message)

        # reload the module
        import nipoppy.workflows._local_executor

        with pytest.raises(ImportError, match=error_message):
            importlib.reload(nipoppy.workflows._local_executor)


class TestInit:
    def test_init_success(self, partial_executor, mocker: pytest_mock.MockFixture):
        """Test that LocalExecutor can be initialized successfully."""
        mocked = mocker.spy(LocalExecutor, "_check_args")
        partial_executor(n_jobs=1, show_progress=False)
        mocked.assert_called_once()


class TestCheckArgs:
    def test_n_jobs_less_than_1(
        self, partial_executor, mocker: pytest_mock.MockFixture
    ):
        """Test that an error is raised when n_jobs < 1."""
        mocker.patch("nipoppy.workflows._local_executor.JOBLIB_INSTALLED", True)

        with pytest.raises(
            InvalidArgumentError, match="must be a positive integer or None"
        ):
            partial_executor(n_jobs=0)

    @pytest.mark.no_xdist
    def test_init_n_jobs_but_no_joblib(
        self,
        partial_executor,
        mocker: pytest_mock.MockFixture,
        reimport_joblib,
    ):
        """Test that an error is raised when joblib is not installed and n_jobs > 1."""
        mocker.patch("nipoppy.workflows._local_executor.JOBLIB_INSTALLED", False)
        with pytest.raises(
            ExecutionError,
            match="An additional dependency is required to enable local parallelization",
        ):
            partial_executor(n_jobs=2)


class TestExecute:
    @pytest.mark.parametrize(
        ["items", "expected_n_success", "is_study_level"],
        [
            (
                [WorkItem("01", "1"), WorkItem("01", "2"), WorkItem("02", "1")],
                3,
                False,
            ),
            (
                [WorkItem("FAIL", "1"), WorkItem("FAIL", "2"), WorkItem("FAIL", "3")],
                0,
                False,
            ),
            (
                [WorkItem("01", "1"), WorkItem("01", "2"), WorkItem("FAIL", "1")],
                2,
                False,
            ),
            ([WorkItem(None, None)], 1, True),
        ],
    )
    def test_execute(
        self,
        items,
        expected_n_success,
        is_study_level,
        partial_executor,
        mocker: pytest_mock.MockFixture,
    ):
        """Test result parsing."""
        executor: LocalExecutor = partial_executor()

        mocked_log_summary_message = mocker.spy(
            nipoppy.workflows._local_executor, "_log_summary_message"
        )
        mocked_get_return_code = mocker.spy(
            nipoppy.workflows._local_executor, "_get_return_code"
        )

        return_code, successful_items, failed_items = executor.execute(items)

        mocked_log_summary_message.assert_called_once_with(
            expected_n_success, len(items), is_study_level=is_study_level
        )

        mocked_get_return_code.assert_called_once_with(expected_n_success, len(items))
        assert return_code == mocked_get_return_code.spy_return

        assert len(successful_items) == expected_n_success
        assert len(failed_items) == len(items) - expected_n_success
        assert (set(successful_items) | set(failed_items)) == set(items)
        assert len(executor.results) == len(items)
        assert all(result in ("SUCCESS", None) for result in executor.results)


class TestWorkFnWrapper:
    def test_success(self, partial_executor):
        """Test result on success."""
        executor: LocalExecutor = partial_executor()
        item = WorkItem("01", "1")
        status, result = executor._work_fn_wrapper(item)
        assert status is True
        assert result == "SUCCESS"

    def test_failure(self, partial_executor):
        """Test result on failure."""
        executor: LocalExecutor = partial_executor()
        item = WorkItem("FAIL", "1")
        status, result = executor._work_fn_wrapper(item)
        assert status is False
        assert result is None


class TestGetStatusesAndResults:
    @pytest.mark.parametrize("show_progress", [True, False])
    def test_no_joblib(
        self,
        partial_executor,
        show_progress: bool,
        mocker: pytest_mock.MockFixture,
        reimport_joblib,
    ):
        """Test that joblib is not used when n_jobs=1."""
        executor: LocalExecutor = partial_executor(
            n_jobs=1, show_progress=show_progress
        )
        participants_sessions = [("01", "1"), ("01", "2"), ("01", "3"), ("02", "1")]

        # pretend that joblib is not installed
        _mock_joblib_import_error(mocker, "No module named 'joblib'")

        # reload the module
        # fmt: off
        import nipoppy.workflows._local_executor
        importlib.reload(nipoppy.workflows._local_executor)
        # check that mocking/reloading worked
        from nipoppy.workflows._local_executor import (  # noqa: F401
            JOBLIB_INSTALLED,
        )
        assert not JOBLIB_INSTALLED
        # fmt: on

        # also mock joblib.delayed which is not supposed to be called
        # when joblib is not installed
        mocked_delayed = mocker.spy(nipoppy.workflows._local_executor, "delayed")

        results = executor._get_statuses_and_results(participants_sessions)
        mocked_delayed.assert_not_called()
        assert len(results) == len(participants_sessions)

    @pytest.mark.parametrize("show_progress", [True, False])
    def test_with_joblib(
        self, partial_executor, show_progress: bool, mocker: pytest_mock.MockFixture
    ):
        """Test that joblib is not used."""
        # fmt: off
        # make sure joblib is installed
        import nipoppy.workflows._local_executor
        from nipoppy.workflows._local_executor import JOBLIB_INSTALLED
        assert JOBLIB_INSTALLED, "joblib must be installed"
        # fmt: on

        executor: LocalExecutor = partial_executor(
            n_jobs=10, show_progress=show_progress
        )
        participants_sessions = [("01", "1"), ("01", "2"), ("01", "3"), ("02", "1")]

        mocked_delayed = mocker.spy(nipoppy.workflows._local_executor, "delayed")

        results = executor._get_statuses_and_results(participants_sessions)
        mocked_delayed.assert_called_once()
        assert len(results) == len(participants_sessions)

    def test_with_progress_bar(self, partial_executor, mocker: pytest_mock.MockFixture):
        """Test that progress bar is shown."""
        executor = partial_executor(show_progress=True)
        participants_sessions = [("001", "1")]

        mocked_track = mocker.patch(
            "nipoppy.workflows._local_executor.rich.progress.track"
        )

        executor._get_statuses_and_results(participants_sessions)
        mocked_track.assert_called_once()

    @pytest.mark.parametrize(
        "show_progress,participants_sessions", [(False, [("001", "1")]), (True, [])]
    )
    def test_no_progress_bar(
        self,
        partial_executor,
        show_progress,
        participants_sessions,
        mocker: pytest_mock.MockFixture,
    ):
        """Test that progress bar is not shown."""
        executor: LocalExecutor = partial_executor(
            n_jobs=1, show_progress=show_progress
        )

        mocked_track = mocker.patch(
            "nipoppy.workflows._local_executor.rich.progress.track"
        )

        executor._get_statuses_and_results(participants_sessions)
        mocked_track.assert_not_called()
