"""Tests for the subprocess runner utilities."""

import logging
import subprocess
from pathlib import Path

import pytest

from nipoppy.utils.subprocess_runner import (
    LogPrefix,
    _log_command,
    run_command,
)

pytestmark = pytest.mark.no_xdist


@pytest.mark.parametrize("command", ["echo x", "echo y"])
def test_log_command(command, caplog: pytest.LogCaptureFixture):
    _log_command(command)
    assert caplog.records
    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    assert record.message.startswith(LogPrefix.RUN)
    assert command in record.message


def test_log_command_no_markup(caplog: pytest.LogCaptureFixture):
    # message with closing tag
    message = "[/]"

    # this should not raise a rich markup error
    run_command(["echo", message])
    assert message in caplog.text


def test_run_command(tmp_path: Path):
    fpath = tmp_path / "test.txt"
    process = run_command(["touch", str(fpath)])
    assert isinstance(process, subprocess.Popen)
    assert process.returncode == 0
    assert fpath.exists()


def test_run_command_single_string(tmp_path: Path):
    fpath = tmp_path / "test.txt"
    process = run_command(f"touch {fpath}", shell=True)
    assert isinstance(process, subprocess.Popen)
    assert process.returncode == 0
    assert fpath.exists()


def test_run_command_dry_run(tmp_path: Path):
    fpath = tmp_path / "test.txt"
    command = run_command(["touch", str(fpath)], dry_run=True)
    assert isinstance(command, str)
    assert command == f"touch {fpath}"
    assert not fpath.exists()


def test_run_command_check():
    with pytest.raises(subprocess.CalledProcessError):
        run_command(["which", "probably_fake_command"], check=True)


def test_run_command_no_markup(caplog: pytest.LogCaptureFixture, tmp_path: Path):
    # text with closing tag
    text = "[/]"

    # this should not raise a rich markup error
    fpath_txt = tmp_path / "test.txt"
    fpath_txt.write_text(text)
    run_command(["cat", str(fpath_txt)])
    assert text in caplog.text


def test_run_command_quiet(caplog: pytest.LogCaptureFixture):
    message = "This should be printed"
    run_command(["echo", message], quiet=True)
    assert LogPrefix.RUN not in caplog.text
    assert message in caplog.text


def test_run_command_streams_final_lines(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
):
    """The final drain ensures the last buffered lines are logged.

    Previously the `while process.poll() is None:` loop could exit before
    reading lines written just prior to process termination; this test
    guards against regressions of that fix.
    """
    final_stdout_line = "final-stdout-line"
    final_stderr_line = "final-stderr-line"

    # Force the race deterministically: make the first poll() call wait for
    # the subprocess to exit. That way, the `while process.poll() is None`
    # loop in run_command never enters its body, so only the post-loop
    # "final drain" can capture the output.
    original_poll = subprocess.Popen.poll

    def wait_then_poll(self, *args, **kwargs):
        if not getattr(self, "_first_poll_done", False):
            self._first_poll_done = True
            self.wait()
        return original_poll(self, *args, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "poll", wait_then_poll)

    caplog.set_level(logging.DEBUG)

    run_command(
        [
            "sh",
            "-c",
            f"echo {final_stdout_line}; echo {final_stderr_line} >&2",
        ],
        quiet=True,  # suppress the [RUN] line so assertions only match process output
    )

    assert f"{LogPrefix.RUN_STDOUT} {final_stdout_line}" in caplog.text
    assert f"{LogPrefix.RUN_STDERR} {final_stderr_line}" in caplog.text
