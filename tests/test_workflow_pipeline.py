"""Tests for _PipelineWorkflow, PipelineRunner, and PipelineTracker."""

from pathlib import Path

import pytest

from nipoppy.config import Config, PipelineConfig, SingularityConfig
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.workflows.pipeline import PipelineRunner, _PipelineWorkflow


class PipelineWorkflow(_PipelineWorkflow):
    def run_single(self, subject: str, session: str):
        """Run on a single subject/session."""
        self.logger.info(f"Running on {subject}/{session}")

    @property
    def config(self) -> Config:
        """Override the config."""
        return Config(
            DATASET_NAME="my_dataset",
            SESSIONS=["ses-1"],
            VISITS=["1"],
            PROC_PIPELINES={
                # built-in pipeline
                "fmriprep": {
                    "23.1.3": {
                        "CONTAINER": "fmriprep.sif",
                        "INVOCATION": {"arg1": "val1"},
                    }
                },
                # user-added pipeline
                "my_pipeline": {
                    "1.0": {
                        "CONTAINER": "my_container.sif",
                        "DESCRIPTOR": {},
                        "INVOCATION": {"arg1": "val1"},
                    }
                },
            },
        )


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


def test_config_properties():
    workflow = PipelineWorkflow(
        dpath_root="my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )
    assert isinstance(workflow.pipeline_config, PipelineConfig)
    assert isinstance(workflow.singularity_config, SingularityConfig)
    assert isinstance(workflow.singularity_command, str)


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version", [("my_pipeline", "1.0"), ("fmriprep", "23.1.3")]
)
def test_descriptor(pipeline_name, pipeline_version, tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = PipelineWorkflow(dpath_root, pipeline_name, pipeline_version)
    assert isinstance(workflow.descriptor, dict)


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version", [("my_pipeline", "1.0"), ("fmriprep", "23.1.3")]
)
def test_invocation(pipeline_name, pipeline_version, tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = PipelineWorkflow(dpath_root, pipeline_name, pipeline_version)
    assert isinstance(workflow.invocation, dict)


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


def test_runner(tmp_path: Path):
    pipeline_name = "dummy_pipeline"
    pipeline_version = "1.0.0"
    runner = PipelineRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
    )
    runner.config = Config(
        DATASET_NAME="my_dataset",
        SESSIONS=["ses-BL", "ses-V04"],
        PROC_PIPELINES={
            pipeline_name: {
                pipeline_version: {
                    "DESCRIPTOR": {
                        "name": pipeline_name,
                        "tool-version": pipeline_version,
                        "description": "A dummy pipeline for testing",
                        "schema-version": "0.5",
                        "command-line": "echo [ARG1] [ARG2] [[NIPOPPY_DPATH_BIDS]]",
                        "inputs": [
                            {
                                "id": "arg1",
                                "name": "arg1",
                                "type": "String",
                                "command-line-flag": "--arg1",
                                "value-key": "[ARG1]",
                            },
                            {
                                "id": "arg2",
                                "name": "arg2",
                                "type": "Number",
                                "command-line-flag": "--arg2",
                                "value-key": "[ARG2]",
                            },
                        ],
                    },
                    "INVOCATION": {
                        "arg1": "[[NIPOPPY_PARTICIPANT]] [[NIPOPPY_SESSION]]",
                        "arg2": 10,
                    },
                }
            }
        },
    )
    participant = "01"
    session = "ses-BL"
    descriptor_str, invocation_str = runner.run_single(participant, session)

    assert "[[NIPOPPY_DPATH_BIDS]]" not in descriptor_str
    assert "[[NIPOPPY_PARTICIPANT]]" not in invocation_str
    assert "[[NIPOPPY_SESSION]]" not in invocation_str
