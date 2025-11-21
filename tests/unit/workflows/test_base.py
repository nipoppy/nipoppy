"""Tests for the BaseWorkflow class."""

import logging
import subprocess
from pathlib import Path

import pytest

from nipoppy.workflows.base import BaseWorkflow


@pytest.fixture()
def workflow():
    class DummyWorkflow(BaseWorkflow):
        def run_main(self):
            pass

    workflow = DummyWorkflow(name="my_workflow")

    return workflow


def test_abstract_class():
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseWorkflow(None, None)


def test_init(workflow: BaseWorkflow):
    assert workflow.name == "my_workflow"
    assert workflow.return_code == 0


@pytest.mark.parametrize("command", ["echo x", "echo y"])
@pytest.mark.parametrize("prefix_run", ["[RUN]", "<run>"])
@pytest.mark.no_xdist
def test_log_command(
    workflow: BaseWorkflow, command, prefix_run, caplog: pytest.LogCaptureFixture
):
    workflow.log_prefix_run = prefix_run
    workflow.log_command(command)
    assert caplog.records
    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    assert record.message.startswith(prefix_run)
    assert command in record.message


@pytest.mark.no_xdist
def test_log_command_no_markup(
    workflow: BaseWorkflow, caplog: pytest.LogCaptureFixture
):
    # message with closing tag
    message = "[/]"

    # this should not raise a rich markup error
    workflow.run_command(["echo", message])
    assert message in caplog.text


def test_run_command(workflow: BaseWorkflow, tmp_path: Path):
    fpath = tmp_path / "test.txt"
    process = workflow.run_command(["touch", fpath])
    assert process.returncode == 0
    assert fpath.exists()


def test_run_command_single_string(workflow: BaseWorkflow, tmp_path: Path):
    fpath = tmp_path / "test.txt"
    process = workflow.run_command(f"touch {fpath}", shell=True)
    assert process.returncode == 0
    assert fpath.exists()


def test_run_command_dry_run(workflow: BaseWorkflow, tmp_path: Path):
    workflow.dry_run = True
    fpath = tmp_path / "test.txt"
    command = workflow.run_command(["touch", fpath])
    assert command == f"touch {fpath}"
    assert not fpath.exists()


def test_run_command_check(workflow: BaseWorkflow):
    with pytest.raises(subprocess.CalledProcessError):
        workflow.run_command(["which", "probably_fake_command"], check=True)


@pytest.mark.no_xdist
def test_run_command_no_markup(
    workflow: BaseWorkflow, caplog: pytest.LogCaptureFixture, tmp_path: Path
):
    # text with closing tag
    text = "[/]"

    # this should not raise a rich markup error
    fpath_txt = tmp_path / "test.txt"
    fpath_txt.write_text(text)
    workflow.run_command(["cat", fpath_txt])
    assert text in caplog.text


@pytest.mark.no_xdist
def test_run_command_quiet(workflow: BaseWorkflow, caplog: pytest.LogCaptureFixture):
    message = "This should be printed"
    workflow.run_command(["echo", message], quiet=True)
    assert workflow.log_prefix_run not in caplog.text
    assert message in caplog.text


def test_run(workflow: BaseWorkflow):
    assert workflow.run() is None
