"""Tests for PipelineRunner."""

from pathlib import Path

import pytest
from fids import fids

from nipoppy.config.base import Config
from nipoppy.utils import strip_session
from nipoppy.workflows.runner import PipelineRunner


@pytest.mark.parametrize("simulate", [True, False])
def test_runner(simulate, tmp_path: Path):
    pipeline_name = "dummy_pipeline"
    pipeline_version = "1.0.0"
    runner = PipelineRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        simulate=simulate,
    )
    runner.config = Config(
        DATASET_NAME="my_dataset",
        SESSIONS=["ses-BL", "ses-V04"],
        SINGULARITY_CONFIG={"COMMAND": "echo"},  # dummy command
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
                    "SINGULARITY_CONFIG": {
                        "COMMAND": "echo",
                    },
                }
            }
        },
    )

    participant = "01"
    session = "ses-BL"

    fids.create_fake_bids_dataset(
        runner.layout.dpath_bids,
        subjects=participant,
        sessions=strip_session(session),
    )

    runner.dpath_pipeline_output.mkdir(parents=True, exist_ok=True)
    runner.dpath_pipeline_work.mkdir(parents=True, exist_ok=True)
    descriptor_str, invocation_str = runner.run_single(participant, session)

    assert "[[NIPOPPY_DPATH_BIDS]]" not in descriptor_str
    assert "[[NIPOPPY_PARTICIPANT]]" not in invocation_str
    assert "[[NIPOPPY_SESSION]]" not in invocation_str
