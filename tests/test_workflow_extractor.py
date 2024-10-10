"""Tests for BidsConversionWorkflow."""

from pathlib import Path

import pytest

from nipoppy.config.main import Config
from nipoppy.config.pipeline import ExtractionPipelineConfig
from nipoppy.tabular.bagel import Bagel
from nipoppy.utils import participant_id_to_bids_participant, session_id_to_bids_session
from nipoppy.workflows.extractor import ExtractionRunner

from .conftest import create_empty_dataset, get_config


@pytest.fixture
def config() -> Config:
    return get_config(
        extraction_pipelines=[
            {
                "NAME": "freesurfer",
                "VERSION": "7.3.2",
                "STEPS": [{}],
            },
            {
                "NAME": "freesurfer",
                "VERSION": "6.0.1",
                "STEPS": [{}],
            },
            {
                "NAME": "fmriprep",
                "VERSION": "23.1.3",
                "STEPS": [{}],
            },
        ]
    )


@pytest.fixture(scope="function")
def extractor(tmp_path: Path) -> ExtractionRunner:
    return ExtractionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="freesurfer",
        pipeline_version="7.3.2",
    )


def test_setup(extractor: ExtractionRunner, config: Config):
    create_empty_dataset(extractor.dpath_root)
    config.save(extractor.layout.fpath_config)

    assert not extractor.dpath_pipeline_idps.exists()
    extractor.run_setup()
    assert extractor.dpath_pipeline_idps.exists()


@pytest.mark.parametrize(
    "bagel_data,participant_id,session_id,expected",
    [
        (
            [
                ["S01", "1", Bagel.status_success],
                ["S01", "2", Bagel.status_incomplete],
                ["S01", "3", Bagel.status_fail],
                ["S02", "1", Bagel.status_unavailable],
                ["S02", "2", Bagel.status_success],
            ],
            None,
            None,
            [("S01", "1"), ("S02", "2")],
        ),
        (
            [
                ["P01", "A", Bagel.status_success],
                ["P01", "B", Bagel.status_success],
                ["P02", "B", Bagel.status_success],
            ],
            "P01",
            "B",
            [("P01", "B")],
        ),
    ],
)
def test_get_participants_sessions_to_run(
    extractor: ExtractionRunner,
    bagel_data,
    participant_id,
    session_id,
    expected,
):
    extractor.bagel = Bagel().add_or_update_records(
        records=[
            {
                Bagel.col_participant_id: data[0],
                Bagel.col_session_id: data[1],
                Bagel.col_bids_participant: participant_id_to_bids_participant(data[0]),
                Bagel.col_bids_session: session_id_to_bids_session(data[1]),
                Bagel.col_pipeline_name: extractor.pipeline_name,
                Bagel.col_pipeline_version: extractor.pipeline_version,
                Bagel.col_pipeline_complete: data[2],
            }
            for data in bagel_data
        ]
    )
    assert [
        tuple(x)
        for x in extractor.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


@pytest.mark.parametrize(
    "pipeline_name,expected_version",
    [
        ("freesurfer", "7.3.2"),
        ("fmriprep", "23.1.3"),
    ],
)
def test_check_pipeline_version(
    pipeline_name, expected_version, config: Config, tmp_path: Path
):
    workflow = ExtractionRunner(
        dpath_root=tmp_path,
        pipeline_name=pipeline_name,
        pipeline_version=None,
    )
    config.save(workflow.layout.fpath_config)
    workflow.check_pipeline_version()
    assert workflow.pipeline_version == expected_version


def test_pipeline_config(extractor: ExtractionRunner, config: Config):
    config.save(extractor.layout.fpath_config)
    assert isinstance(extractor.pipeline_config, ExtractionPipelineConfig)
