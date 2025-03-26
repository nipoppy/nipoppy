"""Tests for the processing status table."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from nipoppy.tabular.processing_status import ProcessingStatus, ProcessingStatusModel

from .conftest import DPATH_TEST_DATA


@pytest.mark.parametrize(
    "data",
    [
        {
            ProcessingStatus.col_participant_id: "1",
            ProcessingStatus.col_bids_participant_id: "sub-1",
            ProcessingStatus.col_session_id: "01",
            ProcessingStatus.col_pipeline_name: "my_pipeline",
            ProcessingStatus.col_pipeline_version: "1.0",
            ProcessingStatus.col_pipeline_step: "a_step",
            ProcessingStatus.col_status: ProcessingStatus.status_success,
        },
        {
            ProcessingStatus.col_participant_id: "2",
            ProcessingStatus.col_session_id: "02",
            ProcessingStatus.col_pipeline_name: "my_other_pipeline",
            ProcessingStatus.col_pipeline_version: "2.0",
            ProcessingStatus.col_pipeline_step: "another_step",
            ProcessingStatus.col_status: ProcessingStatus.status_fail,
        },
    ],
)
def test_model(data):
    processing_status_record = ProcessingStatusModel(**data)
    assert set(processing_status_record.model_fields.keys()) == {
        ProcessingStatus.col_participant_id,
        ProcessingStatus.col_bids_participant_id,
        ProcessingStatus.col_session_id,
        ProcessingStatus.col_pipeline_name,
        ProcessingStatus.col_pipeline_version,
        ProcessingStatus.col_pipeline_step,
        ProcessingStatus.col_status,
        ProcessingStatus.col_bids_session_id,
    }


@pytest.mark.parametrize(
    "participant_id,expected_bids_id", [("01", "sub-01"), ("1", "sub-1")]
)
def test_model_bids_id(participant_id, expected_bids_id):
    model = ProcessingStatusModel(
        participant_id=participant_id,
        session_id="01",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        pipeline_step="step1",
        status=ProcessingStatus.status_success,
    )
    assert model.bids_participant_id == expected_bids_id


@pytest.mark.parametrize(
    "status",
    [
        ProcessingStatus.status_success,
        ProcessingStatus.status_fail,
        ProcessingStatus.status_incomplete,
        ProcessingStatus.status_unavailable,
    ],
)
def test_model_status(status):
    model = ProcessingStatusModel(
        participant_id="1",
        session_id="01",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        pipeline_step="step1",
        status=status,
    )
    assert model.status == status


def test_model_status_invalid():
    with pytest.raises(ValidationError):
        ProcessingStatusModel(
            participant_id="1",
            session_id="01",
            pipeline_name="my_pipeline",
            pipeline_version="1.0",
            pipeline_step="step1",
            status="BAD_STATUS",
        )


@pytest.mark.parametrize(
    "data_orig,data_new,data_expected",
    [
        (
            [],
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "1",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
            ],
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "1",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
            ],
        ),
        (
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "1",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_fail,
                },
            ],
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "1",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
            ],
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "1",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
            ],
        ),
        (
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "1",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_fail,
                },
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "2",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_unavailable,
                },
            ],
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "2",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "3",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
            ],
            [
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "1",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_fail,
                },
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "2",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
                {
                    ProcessingStatus.col_participant_id: "01",
                    ProcessingStatus.col_session_id: "3",
                    ProcessingStatus.col_pipeline_name: "my_pipeline",
                    ProcessingStatus.col_pipeline_version: "1.0",
                    ProcessingStatus.col_pipeline_step: "step1",
                    ProcessingStatus.col_status: ProcessingStatus.status_success,
                },
            ],
        ),
    ],
)
def test_add_or_update_records(data_orig, data_new, data_expected):
    processing_status_table = ProcessingStatus(data_orig).validate()
    processing_status_table = processing_status_table.add_or_update_records(data_new)
    expected_table = ProcessingStatus(data_expected).validate()
    assert processing_status_table.equals(expected_table)


@pytest.mark.parametrize(
    "data,pipeline_name,pipeline_version,pipeline_step,participant_id,session_id,expected",  # noqa E501
    [
        (
            [
                [
                    "01",
                    "1",
                    "pipeline1",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                ["02", "1", "pipeline1", "1.0", "step1", ProcessingStatus.status_fail],
                [
                    "03",
                    "1",
                    "pipeline1",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_incomplete,
                ],
                [
                    "04",
                    "1",
                    "pipeline1",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_unavailable,
                ],
            ],
            "pipeline1",
            "1.0",
            "step1",
            None,
            None,
            [("01", "1")],
        ),
        (
            [
                [
                    "S01",
                    "BL",
                    "pipeline1",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S01",
                    "BL",
                    "pipeline1",
                    "2.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S01",
                    "BL",
                    "pipeline2",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S01",
                    "BL",
                    "pipeline2",
                    "2.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
            ],
            "pipeline2",
            "2.0",
            "step1",
            None,
            None,
            [("S01", "BL")],
        ),
        (
            [
                [
                    "S01",
                    "BL",
                    "pipeline1",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S01",
                    "BL",
                    "pipeline1",
                    "2.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S01",
                    "BL",
                    "pipeline2",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S01",
                    "M12",
                    "pipeline2",
                    "2.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S02",
                    "BL",
                    "pipeline1",
                    "1.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S02",
                    "BL",
                    "pipeline1",
                    "2.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S02",
                    "BL",
                    "pipeline2",
                    "2.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
                [
                    "S02",
                    "M12",
                    "pipeline2",
                    "2.0",
                    "step1",
                    ProcessingStatus.status_success,
                ],
            ],
            "pipeline2",
            "2.0",
            "step1",
            "S02",
            "M12",
            [("S02", "M12")],
        ),
    ],
)
def test_get_completed_participants_sessions(
    data,
    pipeline_name,
    pipeline_version,
    pipeline_step,
    participant_id,
    session_id,
    expected,
):
    processing_status_table = ProcessingStatus(
        data,
        columns=[
            ProcessingStatus.col_participant_id,
            ProcessingStatus.col_session_id,
            ProcessingStatus.col_pipeline_name,
            ProcessingStatus.col_pipeline_version,
            ProcessingStatus.col_pipeline_step,
            ProcessingStatus.col_status,
        ],
    ).validate()

    assert [
        tuple(x)
        for x in processing_status_table.get_completed_participants_sessions(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant_id=participant_id,
            session_id=session_id,
        )
    ] == expected


@pytest.mark.parametrize(
    "fpath",
    [
        DPATH_TEST_DATA / "bagel1.tsv",
        DPATH_TEST_DATA / "bagel2.tsv",
        Path(__file__).parent
        / ".."
        / "docs"
        / "source"
        / "user_guide"
        / "inserts"
        / "mriqc_bagel.tsv",
    ],
)
def test_load(fpath):
    processing_status_table = ProcessingStatus.load(fpath)
    assert isinstance(processing_status_table, ProcessingStatus)


@pytest.mark.parametrize(
    "fname",
    [
        "bagel_invalid1.tsv",
        "bagel_invalid2.tsv",
    ],
)
def test_load_invalid(fname):
    with pytest.raises(ValueError):
        ProcessingStatus.load(DPATH_TEST_DATA / fname)
