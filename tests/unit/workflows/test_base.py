"""Tests for the BaseWorkflow class."""

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


def test_run(workflow: BaseWorkflow):
    assert workflow.run() is None
