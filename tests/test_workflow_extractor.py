"""Tests for ExtractionWorkflow."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.main import Config
from nipoppy.config.pipeline import ExtractionPipelineConfig
from nipoppy.env import DEFAULT_PIPELINE_STEP_NAME
from nipoppy.tabular.bagel import Bagel
from nipoppy.utils import (
    participant_id_to_bids_participant_id,
    session_id_to_bids_session_id,
)
from nipoppy.workflows.extractor import ExtractionRunner

from .conftest import create_empty_dataset, get_config


@pytest.fixture
def config() -> Config:
    return get_config(
        proc_pipelines=[
            {
                "NAME": "freesurfer",
                "VERSION": "7.3.2",
                "STEPS": [{}],
            },
        ],
        extraction_pipelines=[
            {
                "NAME": "fs_extractor",
                "VERSION": "7.3.2",
                "PROC_DEPENDENCIES": [
                    {
                        "NAME": "freesurfer",
                        "VERSION": "7.3.2",
                    },
                ],
                "STEPS": [{}],
            },
            {
                "NAME": "fs_fmriprep_extractor",
                "VERSION": "1.0.0",
                "PROC_DEPENDENCIES": [
                    {
                        "NAME": "freesurfer",
                        "VERSION": "6.0.1",
                    },
                    {
                        "NAME": "fmriprep",
                        "VERSION": "20.0.7",
                    },
                ],
                "STEPS": [{}],
            },
        ],
    )


@pytest.fixture(scope="function")
def extractor(tmp_path: Path) -> ExtractionRunner:
    return ExtractionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="fs_extractor",
        pipeline_version="7.3.2",
        pipeline_step=DEFAULT_PIPELINE_STEP_NAME,
    )


@pytest.mark.parametrize(
    "attribute,expected",
    [
        ("dpath_pipeline", "derivatives/freesurfer/7.3.2"),
        ("dpath_pipeline_output", "derivatives/freesurfer/7.3.2/output"),
        ("dpath_pipeline_idp", "derivatives/freesurfer/7.3.2/idp"),
    ],
)
def test_paths(extractor: ExtractionRunner, config: Config, attribute, expected):
    extractor.config = config
    assert getattr(extractor, attribute) == extractor.dpath_root / expected


def test_setup(extractor: ExtractionRunner, config: Config):
    create_empty_dataset(extractor.dpath_root)
    config.save(extractor.layout.fpath_config)

    assert not extractor.dpath_pipeline_idp.exists()
    extractor.run_setup()
    assert extractor.dpath_pipeline_idp.exists()


def test_dpath_pipeline(extractor: ExtractionRunner, config: Config):
    config.save(extractor.layout.fpath_config)
    assert (
        extractor.dpath_pipeline
        == extractor.layout.dpath_derivatives / "freesurfer" / "7.3.2"
    )


def test_proc_pipeline_info(config: Config, tmp_path: Path):
    workflow = ExtractionRunner(
        dpath_root=tmp_path,
        pipeline_name="fs_extractor",
        pipeline_version="6.0.1",  # not in PROC_PIPELINES
    )
    config.save(workflow.layout.fpath_config)
    with pytest.raises(ValueError, match="No config found for pipeline with"):
        workflow.proc_pipeline_info


@pytest.mark.parametrize(
    "bagel_data,pipeline_name,pipeline_version,participant_id,session_id,expected",
    [
        (
            [
                ["S01", "1", "freesurfer", "7.3.2", Bagel.status_success],
                ["S01", "2", "freesurfer", "7.3.2", Bagel.status_incomplete],
                ["S01", "3", "freesurfer", "7.3.2", Bagel.status_fail],
                ["S02", "1", "freesurfer", "7.3.2", Bagel.status_unavailable],
                ["S02", "2", "freesurfer", "7.3.2", Bagel.status_success],
            ],
            "fs_extractor",
            "7.3.2",
            None,
            None,
            [("S01", "1"), ("S02", "2")],
        ),
        (
            [
                ["S01", "1", "freesurfer", "7.3.2", Bagel.status_success],
            ],
            "fs_extractor",
            "7.3.2",
            "S02",  # S02 is not in bagel
            "1",
            [],
        ),
        (
            [
                ["P01", "A", "freesurfer", "6.0.1", Bagel.status_success],
                ["P01", "B", "freesurfer", "6.0.1", Bagel.status_fail],
                ["P02", "B", "freesurfer", "6.0.1", Bagel.status_success],
                ["P01", "A", "fmriprep", "20.0.7", Bagel.status_fail],
                ["P01", "B", "fmriprep", "20.0.7", Bagel.status_success],
                ["P02", "B", "fmriprep", "20.0.7", Bagel.status_success],
            ],
            "fs_fmriprep_extractor",
            "1.0.0",
            "P02",
            "B",
            [("P02", "B")],
        ),
    ],
)
def test_get_participants_sessions_to_run(
    bagel_data,
    pipeline_name,
    pipeline_version,
    participant_id,
    session_id,
    expected,
    config: Config,
    tmp_path: Path,
):
    extractor = ExtractionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        pipeline_step=DEFAULT_PIPELINE_STEP_NAME,
    )
    extractor.bagel = Bagel().add_or_update_records(
        records=[
            {
                Bagel.col_participant_id: data[0],
                Bagel.col_session_id: data[1],
                Bagel.col_bids_participant_id: participant_id_to_bids_participant_id(
                    data[0]
                ),
                Bagel.col_bids_session_id: session_id_to_bids_session_id(data[1]),
                Bagel.col_pipeline_name: data[2],
                Bagel.col_pipeline_version: data[3],
                Bagel.col_pipeline_step: DEFAULT_PIPELINE_STEP_NAME,
                Bagel.col_status: data[4],
            }
            for data in bagel_data
        ]
    )
    config.save(extractor.layout.fpath_config)
    assert [
        tuple(x)
        for x in extractor.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


def test_run_single(
    extractor: ExtractionRunner,
    mocker: pytest_mock.MockerFixture,
    config: Config,
):
    extractor.config = config

    mocked_process_container_config = mocker.patch(
        "nipoppy.workflows.runner.PipelineRunner.process_container_config"
    )
    mocked_launch_boutiques_container = mocker.patch(
        "nipoppy.workflows.runner.PipelineRunner.launch_boutiques_run"
    )

    extractor.run_single("S01", "BL")
    assert mocked_process_container_config.call_count == 1
    mocked_process_container_config.assert_called_once_with(
        participant_id="S01",
        session_id="BL",
        bind_paths=[extractor.dpath_pipeline_idp, extractor.dpath_pipeline_output],
    )
    assert mocked_launch_boutiques_container.call_count == 1


def test_check_pipeline_version(config: Config, tmp_path: Path):
    workflow = ExtractionRunner(
        dpath_root=tmp_path,
        pipeline_name="fs_extractor",
        pipeline_version=None,
    )
    config.save(workflow.layout.fpath_config)
    workflow.check_pipeline_version()
    assert workflow.pipeline_version == "7.3.2"


def test_pipeline_config(extractor: ExtractionRunner, config: Config):
    config.save(extractor.layout.fpath_config)
    assert isinstance(extractor.pipeline_config, ExtractionPipelineConfig)
