"""Tests for PipelineSearchWorkflow class."""

import logging

import pandas as pd
import pytest
import pytest_mock

from nipoppy.workflows.pipeline_store.search import PipelineSearchWorkflow
from nipoppy.zenodo_api import ZenodoAPI


@pytest.fixture(scope="function")
def workflow():
    """Fixture for PipelineSearchWorkflow."""
    # use sandbox because for now there are no Nipoppy records on official Zenodo
    return PipelineSearchWorkflow(
        query="mriqc",
        zenodo_api=ZenodoAPI(sandbox=True),
        size=1,
    )


@pytest.fixture(scope="function")
def hits():
    """Fixture for hits."""
    return [
        {
            "id": 12345,
            "title": "Pipeline 1",
            "stats": {"downloads": 4},
            "metadata": {
                "description": "Description 1",
            },
        },
        {
            "id": 67890,
            "title": "Pipeline 2",
            "stats": {"downloads": 100},
            "metadata": {},
        },
    ]


def test_hits_to_df(workflow: PipelineSearchWorkflow, hits: list[dict]):
    df = workflow._hits_to_df(hits)
    assert len(df) == len(hits)

    # order is switched because of sorting by downloads
    assert df.iloc[0]["Zenodo ID"] == 67890
    assert df.iloc[0]["Title"] == "Pipeline 2"
    assert df.iloc[0]["Description"] is None
    assert df.iloc[0]["Downloads"] == 100

    assert df.iloc[1]["Zenodo ID"] == 12345
    assert df.iloc[1]["Title"] == "Pipeline 1"
    assert df.iloc[1]["Description"] == "Description 1"
    assert df.iloc[1]["Downloads"] == 4


def test_df_to_table(workflow: PipelineSearchWorkflow, hits: list[dict]):
    df_hits = pd.DataFrame(hits)
    table = workflow._df_to_table(df_hits)
    assert table.row_count == len(df_hits)
    assert len(table.columns) == len(df_hits.columns)


def test_run_main(
    workflow: PipelineSearchWorkflow,
    hits: list[dict],
    mocker: pytest_mock.MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    df = pd.DataFrame(hits)
    mocked_search_records = mocker.patch.object(
        workflow.zenodo_api,
        "search_records",
        return_value={"hits": hits, "total": 2},
    )
    mocked_hits_to_df = mocker.patch.object(workflow, "_hits_to_df", return_value=df)
    mocked_df_to_table = mocker.patch.object(workflow, "_df_to_table")

    workflow.run()

    mocked_search_records.assert_called_once_with(
        query=workflow.query, keywords=["Nipoppy"], size=workflow.size
    )
    mocked_hits_to_df.assert_called_once_with(hits)
    mocked_df_to_table.assert_called_once_with(df)
    assert "Showing 2 of 2 results" in caplog.text


def test_run_main_no_results(
    workflow: PipelineSearchWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow.query = "fake_pipeline_name"
    workflow.run()

    assert any(
        [
            "No results found for query" in record.message
            and record.levelno == logging.WARNING
            for record in caplog.records
        ]
    )
