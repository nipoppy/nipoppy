"""Tests for PipelineWorkflow."""

import pytest

from nipoppy.workflows.pipeline import _PipelineWorkflow


class PipelineWorkflow(_PipelineWorkflow):
    def run_single(self, subject: str, session: str):
        """Run on a single subject/session."""
        return


@pytest.mark.parametrize(
    "args",
    [
        {
            "dpath_root": "my_dataset",
            "pipeline_name": "my_pipeline",
            "pipeline_version": "1.0",
        },
        {
            "dpath_root": "my_dataset",
            "pipeline_name": "my_other_pipeline",
            "pipeline_version": "2.0",
        },
    ],
)
def test_init(args):
    workflow = PipelineWorkflow(**args)
    assert isinstance(workflow, _PipelineWorkflow)
    assert hasattr(workflow, "pipeline_name")
    assert hasattr(workflow, "pipeline_version")
