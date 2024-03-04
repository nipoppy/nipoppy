"""Tests for PipelineWorkflow."""

from pathlib import Path

import pytest

from nipoppy.tabular.doughnut import Doughnut
from nipoppy.workflows.pipeline import _PipelineWorkflow


class PipelineWorkflow(_PipelineWorkflow):
    def run_single(self, subject: str, session: str):
        """Run on a single subject/session."""
        self.logger.info(f"Running on {subject}/{session}")


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
    assert hasattr(workflow, "participant")
    assert hasattr(workflow, "session")
    assert isinstance(workflow.dpath_pipeline, Path)
    assert isinstance(workflow.dpath_pipeline_work, Path)
    assert isinstance(workflow.dpath_pipeline_output, Path)


@pytest.mark.parametrize("dry_run", [True, False])
def test_run_setup(dry_run: bool, tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        dry_run=dry_run,
    )
    workflow.run_setup()
    for dpath_to_check in [
        workflow.dpath_pipeline,
        workflow.dpath_pipeline_work,
        workflow.dpath_pipeline_output,
    ]:
        assert dpath_to_check.exists() == (not dry_run)

    # run again, should not fail even if directories already exist
    workflow.run_setup()


def test_run_main(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )
    # make an empty doughnut
    Doughnut().save_with_backup(workflow.layout.fpath_doughnut)
    workflow.run_main()
