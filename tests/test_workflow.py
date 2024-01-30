"""Tests for the workflow module."""

import logging
from pathlib import Path

import pytest

from nipoppy.logger import get_logger
from nipoppy.workflow import _Workflow


@pytest.fixture(params=[get_logger("my_logger"), None])
def workflow(request: pytest.FixtureRequest, tmp_path: Path):
    class DummyWorkflow(_Workflow):
        pass

    dpath_root = tmp_path / "my_dataset"
    return DummyWorkflow(
        dpath_root=dpath_root, name="my_workflow", logger=request.param
    )


def test_workflow_init(workflow: _Workflow):
    assert isinstance(workflow.dpath_root, Path)
    assert isinstance(workflow.logger, logging.Logger)


def test_workflow_generate_fpath_log(workflow: _Workflow):
    fpath_log = workflow.generate_fpath_log()
    fpath_log.mkdir(parents=True, exist_ok=True)
    fpath_log.touch()
    assert isinstance(fpath_log, Path)


@pytest.mark.parametrize("command", ["echo x", "echo y"])
@pytest.mark.parametrize("prefix_run", ["[RUN]", "<run>"])
def test_log_command(
    workflow: _Workflow, command, prefix_run, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(level=logging.DEBUG)  # capture all logs
    workflow.log_prefix_run = prefix_run
    workflow.log_command(command)
    assert caplog.records
    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    assert record.message.startswith(prefix_run)
    assert command in record.message


@pytest.mark.parametrize(
    "command_or_args,shell,capture_output,expected",
    [
        ("echo x", False, False, "echo x"),
        (["echo", "y"], False, False, "echo y"),
        ("echo x", False, True, ("x\n", "")),
        (["echo", "y"], False, True, ("y\n", "")),
        ("echo x && echo y 1>&2", True, True, ("x\n", "y\n")),
        (["echo x && echo y 1>&2"], True, True, ("x\n", "y\n")),
    ],
)
@pytest.mark.parametrize("check", [True, False])
def test_run_command(
    workflow: _Workflow, command_or_args, shell, capture_output, expected, check
):
    if capture_output:
        workflow.dry_run = False
    else:
        workflow.dry_run = True

    assert expected == workflow.run_command(
        command_or_args, check=check, shell=shell, capture_output=capture_output
    )
