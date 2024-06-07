"""Tests for BidsConversionWorkflow."""

from pathlib import Path

import pytest

from nipoppy.config.main import Config
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.workflows.bids_conversion import BidsConversionRunner

from .conftest import create_empty_dataset, get_config


@pytest.fixture
def config() -> Config:
    return get_config(
        bids_pipelines=[
            {
                "NAME": "heudiconv",
                "VERSION": "0.12.2",
                "STEPS": [{"NAME": "prepare"}, {"NAME": "convert"}],
            },
            {
                "NAME": "dcm2bids",
                "VERSION": "3.1.0",
                "STEPS": [{"NAME": "prepare"}, {"NAME": "convert"}],
            },
        ]
    )


def test_setup(config: Config, tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    create_empty_dataset(workflow.dpath_root)
    config.save(workflow.layout.fpath_config)
    workflow.run_setup()
    assert not workflow.dpath_pipeline.exists()


@pytest.mark.parametrize(
    "doughnut_data,participant,session,expected",
    [
        (
            [
                {
                    Doughnut.col_participant_id: "S01",
                    Doughnut.col_session: "ses-1",
                    Doughnut.col_organized: True,
                    Doughnut.col_bidsified: False,
                },
                {
                    Doughnut.col_participant_id: "S01",
                    Doughnut.col_session: "ses-2",
                    Doughnut.col_organized: True,
                    Doughnut.col_bidsified: True,
                },
                {
                    Doughnut.col_participant_id: "S02",
                    Doughnut.col_session: "ses-3",
                    Doughnut.col_organized: False,
                    Doughnut.col_bidsified: False,
                },
            ],
            None,
            None,
            [("S01", "ses-1")],
        ),
        (
            [
                {
                    Doughnut.col_participant_id: "P01",
                    Doughnut.col_session: "ses-A",
                    Doughnut.col_organized: True,
                    Doughnut.col_bidsified: False,
                },
                {
                    Doughnut.col_participant_id: "P01",
                    Doughnut.col_session: "ses-B",
                    Doughnut.col_organized: True,
                    Doughnut.col_bidsified: False,
                },
                {
                    Doughnut.col_participant_id: "P02",
                    Doughnut.col_session: "ses-B",
                    Doughnut.col_organized: True,
                    Doughnut.col_bidsified: False,
                },
            ],
            "P01",
            "ses-B",
            [("P01", "ses-B")],
        ),
    ],
)
def test_get_participants_sessions_to_run(
    doughnut_data, participant, session, expected, tmp_path: Path
):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    workflow.doughnut = Doughnut().add_or_update_records(
        records=[
            {
                **data,
                Doughnut.col_visit: data[Doughnut.col_session],
                Doughnut.col_datatype: None,
                Doughnut.col_participant_dicom_dir: "",
                Doughnut.col_dicom_id: "",
                Doughnut.col_bids_id: "",
                Doughnut.col_downloaded: False,
            }
            for data in doughnut_data
        ]
    )
    assert [
        tuple(x)
        for x in workflow.get_participants_sessions_to_run(
            participant=participant, session=session
        )
    ] == expected
