"""Tests for PipelineSearchWorkflow class."""

import logging

import pandas as pd
import pytest
import pytest_mock
from rich.table import Table

from nipoppy.workflows.pipeline_store.search import PipelineSearchWorkflow


@pytest.fixture(scope="function")
def workflow(mocker: pytest_mock.MockerFixture):
    """Fixture for PipelineSearchWorkflow."""
    # use sandbox because for now there are no Nipoppy records on official Zenodo
    return PipelineSearchWorkflow(
        query="mriqc",
        zenodo_api=mocker.MagicMock(),
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
                "description": "<div><p>\nDescription 1: <PIPELINE_NAME>\n</p></div>",
            },
            "doi_url": "fake_doi_url_12345",
        },
        {
            "id": 67890,
            "title": "Pipeline 2",
            "stats": {"downloads": 100},
            "metadata": {},
            "doi_url": "fake_doi_url_67890",
        },
    ]


def test_hits_to_df(workflow: PipelineSearchWorkflow, hits: list[dict]):
    workflow.size = len(hits)
    df = workflow._hits_to_df(hits)
    assert len(df) == workflow.size

    # order is switched because of sorting by downloads
    assert df.iloc[0]["Zenodo ID"] == "[link=fake_doi_url_67890]67890[/link]"
    assert df.iloc[0]["Title"] == "Pipeline 2"
    assert df.iloc[0]["Description"] is None
    assert df.iloc[0]["Downloads"] == 100

    assert df.iloc[1]["Zenodo ID"] == "[link=fake_doi_url_12345]12345[/link]"
    assert df.iloc[1]["Title"] == "Pipeline 1"
    assert df.iloc[1]["Description"] == "Description 1: <PIPELINE_NAME>"
    assert df.iloc[1]["Downloads"] == 4


@pytest.mark.parametrize(
    "console_width, is_description_hidden",
    [
        (80, True),
        (120, False),
    ],
)
def test_df_to_table(
    workflow: PipelineSearchWorkflow,
    console_width: int,
    is_description_hidden: bool,
    monkeypatch: pytest.MonkeyPatch,
):
    import nipoppy.workflows.pipeline_store.search as search_module

    monkeypatch.setattr(search_module, "CONSOLE_WIDTH", console_width)
    df_hits = pd.DataFrame(
        [
            {
                "Zenodo ID": "[link=fake_doi_url]12345[/link]",
                "Title": "Pipeline 1",
                "Description": "Description 1: <PIPELINE_NAME>",
                "Downloads": 4,
            },
            {
                "Zenodo ID": "[link=fake_doi_url]67890[/link]",
                "Title": "Pipeline 2",
                "Description": None,
                "Downloads": 100,
            },
        ]
    )
    table = workflow._df_to_table(df_hits)
    assert table.row_count == len(df_hits)
    if is_description_hidden:
        assert len(table.columns) == len(df_hits.columns) - 1
    else:
        assert len(table.columns) == len(df_hits.columns)


def test_run_main(
    workflow: PipelineSearchWorkflow,
    hits: list[dict],
    mocker: pytest_mock.MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    df = pd.DataFrame(hits)

    mocked_console_status = mocker.patch(
        "nipoppy.workflows.pipeline_store.install.CONSOLE_STDOUT.status",
    )

    # mock search_records and downstream methods
    workflow.zenodo_api.search_records.return_value = {"hits": hits, "total": 2}
    mocked_hits_to_df = mocker.patch.object(workflow, "_hits_to_df", return_value=df)
    mocked_df_to_table = mocker.patch.object(
        workflow, "_df_to_table", return_value=Table()
    )

    workflow.run()

    workflow.zenodo_api.search_records.assert_called_once_with(
        query=workflow.query, keywords=["Nipoppy"], size=workflow._api_search_size
    )
    mocked_hits_to_df.assert_called_once_with(hits)
    mocked_df_to_table.assert_called_once_with(df)
    assert "Showing 1 of 2 results" in caplog.text
    assert " (use --size to show more)" in caplog.text
    mocked_console_status.assert_called_once()


def test_run_main_no_results(
    workflow: PipelineSearchWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    # mock search results
    workflow.zenodo_api.search_records.return_value = {"hits": [], "total": 0}

    workflow.query = "fake_pipeline_name"
    workflow.run()

    assert any(
        [
            "No results found for query" in record.message
            and record.levelno == logging.WARNING
            for record in caplog.records
        ]
    )


def test_run_main_all_results(
    workflow: PipelineSearchWorkflow,
    hits: list[dict],
    caplog: pytest.LogCaptureFixture,
):
    workflow.size = len(hits)

    # mock search results
    workflow.zenodo_api.search_records.return_value = {"hits": hits, "total": len(hits)}

    workflow.run()

    assert "(use --size to show more)" not in caplog.text
