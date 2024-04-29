"""Tests for the bagel."""

import pytest
from pydantic import ValidationError

from nipoppy.tabular.bagel import Bagel, BagelModel


@pytest.mark.parametrize(
    "data",
    [
        {
            Bagel.col_participant_id: "1",
            Bagel.col_bids_id: "sub-1",
            Bagel.col_session: "ses-01",
            Bagel.col_pipeline_name: "my_pipeline",
            Bagel.col_pipeline_version: "1.0",
            Bagel.col_pipeline_complete: Bagel.status_success,
        },
        {
            Bagel.col_participant_id: "2",
            Bagel.col_session: "ses-02",
            Bagel.col_pipeline_name: "my_other_pipeline",
            Bagel.col_pipeline_version: "2.0",
            Bagel.col_pipeline_complete: Bagel.status_fail,
        },
    ],
)
def test_model(data):
    BagelModel(**data)


@pytest.mark.parametrize(
    "participant_id,expected_bids_id", [("01", "sub-01"), ("1", "sub-1")]
)
def test_model_bids_id(participant_id, expected_bids_id):
    model = BagelModel(
        participant_id=participant_id,
        session="ses-01",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        pipeline_complete=Bagel.status_success,
    )
    assert model.bids_id == expected_bids_id


@pytest.mark.parametrize(
    "status",
    [
        Bagel.status_success,
        Bagel.status_fail,
        Bagel.status_incomplete,
        Bagel.status_unavailable,
    ],
)
def test_model_status(status):
    model = BagelModel(
        participant_id="1",
        session="ses-01",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        pipeline_complete=status,
    )
    assert model.pipeline_complete == status


def test_model_status_invalid():
    with pytest.raises(ValidationError):
        BagelModel(
            participant_id="1",
            session="ses-01",
            pipeline_name="my_pipeline",
            pipeline_version="1.0",
            pipeline_complete="BAD_STATUS",
        )


@pytest.mark.parametrize(
    "data_orig,data_new,data_expected",
    [
        (
            [],
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-1",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
            ],
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-1",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
            ],
        ),
        (
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-1",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_fail,
                },
            ],
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-1",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
            ],
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-1",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
            ],
        ),
        (
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-1",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_fail,
                },
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-2",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_unavailable,
                },
            ],
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-2",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-3",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
            ],
            [
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-1",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_fail,
                },
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-2",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
                {
                    Bagel.col_participant_id: "01",
                    Bagel.col_session: "ses-3",
                    Bagel.col_pipeline_name: "my_pipeline",
                    Bagel.col_pipeline_version: "1.0",
                    Bagel.col_pipeline_complete: Bagel.status_success,
                },
            ],
        ),
    ],
)
def test_add_or_update_records(data_orig, data_new, data_expected):
    bagel = Bagel(data_orig).validate()
    bagel = bagel.add_or_update_records(data_new)
    expected_bagel = Bagel(data_expected).validate()
    assert bagel.equals(expected_bagel)
