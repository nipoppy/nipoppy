"""Tests for PipelineRunner."""

from pathlib import Path

import pytest
from fids import fids

from nipoppy.config.main import Config
from nipoppy.utils import strip_session
from nipoppy.workflows.runner import PipelineRunner

from .conftest import create_empty_dataset, get_config


@pytest.fixture
def config():
    return get_config(
        visits=["BL", "V04"],
        container_config={"COMMAND": "echo"},  # dummy command
        proc_pipelines={
            "dummy_pipeline": {
                "1.0.0": {
                    "DESCRIPTOR": {
                        "name": "dummy_pipeline",
                        "tool-version": "1.0.0",
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
                    "CONTAINER_CONFIG": {
                        "COMMAND": "echo",
                    },
                }
            }
        },
    )


def test_run_setup(config: Config, tmp_path: Path):
    runner = PipelineRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="dummy_pipeline",
        pipeline_version="1.0.0",
    )
    create_empty_dataset(runner.dpath_root)
    config.save(runner.layout.fpath_config)
    runner.run_setup()
    assert runner.dpath_pipeline_output.exists()
    assert runner.dpath_pipeline_work.exists()


@pytest.mark.parametrize("simulate", [True, False])
def test_launch_boutiques_run(simulate, config: Config, tmp_path: Path):
    runner = PipelineRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="dummy_pipeline",
        pipeline_version="1.0.0",
        simulate=simulate,
    )
    config.save(runner.layout.fpath_config)

    participant = "01"
    session = "ses-BL"

    fids.create_fake_bids_dataset(
        runner.layout.dpath_bids,
        subjects=participant,
        sessions=strip_session(session),
    )

    runner.dpath_pipeline_output.mkdir(parents=True, exist_ok=True)
    runner.dpath_pipeline_work.mkdir(parents=True, exist_ok=True)
    descriptor_str, invocation_str = runner.launch_boutiques_run(
        participant, session, container_command=""
    )

    assert "[[NIPOPPY_DPATH_BIDS]]" not in descriptor_str
    assert "[[NIPOPPY_PARTICIPANT]]" not in invocation_str
    assert "[[NIPOPPY_SESSION]]" not in invocation_str
