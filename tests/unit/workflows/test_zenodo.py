"""Test for the ZenodoUploadWorkflow class."""

from contextlib import nullcontext

import pytest
import pytest_mock

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PipelineTypeEnum
from nipoppy.pipeline_validation import _load_pipeline_config_file
from nipoppy.workflows.pipeline_store.zenodo import (
    ZenodoUploadWorkflow,
    _is_same_pipeline,
)
from nipoppy.zenodo_api import ZenodoAPI, ZenodoAPIError
from tests.conftest import TEST_PIPELINE

DATASET_PATH = "my_dataset"


@pytest.fixture(scope="function")
def zenodo_api_mocker(mocker: pytest_mock.MockerFixture):
    mocker.patch(
        "nipoppy.zenodo_api.ZenodoAPI.upload_pipeline",
    )
    mocker.patch(
        "nipoppy.workflows.pipeline_store.zenodo.ZenodoUploadWorkflow._get_pipeline_metadata",
    )
    mocker.patch(
        "nipoppy.workflows.pipeline_store.zenodo.check_pipeline_bundle",
    )
    yield mocker


def test_upload(mocker: pytest_mock.MockerFixture):
    upload_pipeline = mocker.patch(
        "nipoppy.zenodo_api.ZenodoAPI.upload_pipeline",
    )
    get_pipeline_metadata = mocker.patch(
        "nipoppy.workflows.pipeline_store.zenodo.ZenodoUploadWorkflow._get_pipeline_metadata",
    )
    validator = mocker.patch(
        "nipoppy.workflows.pipeline_store.zenodo.check_pipeline_bundle",
    )

    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,
        zenodo_api=zenodo_api,
        assume_yes=True,
        force=True,
    )
    workflow.run_main()

    upload_pipeline.assert_called_once()
    get_pipeline_metadata.assert_called_once()
    validator.assert_called_once()


def test_get_pipeline_metadata(datetime_fixture):  # noqa F811
    expected = {
        "metadata": {
            "title": "Upload test",
            "description": "This is a test upload",
            "creators": [
                {
                    "person_or_org": {
                        "given_name": "Nipoppy",
                        "family_name": "Test",
                        "type": "personal",
                    }
                }
            ],
            "publication_date": "2024-04-04",
            "publisher": "Nipoppy",
            "resource_type": {"id": "software"},
            "subjects": [
                {"subject": "Nipoppy"},
                {"subject": "pipeline_type:processing"},
                {"subject": "pipeline_name:fmriprep"},
                {"subject": "pipeline_version:24.1.1"},
                {"subject": "schema_version:1"},
            ],
        }
    }

    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,
        zenodo_api=zenodo_api,
    )

    pipeline_config = _load_pipeline_config_file(TEST_PIPELINE / "config.json")

    results = workflow._get_pipeline_metadata(
        zenodo_metadata_file=TEST_PIPELINE / "zenodo.json",
        pipeline_config=pipeline_config,
    )

    assert results == expected


@pytest.mark.parametrize(
    "pipeline_config, zenodo_metadata, expected",
    [
        (
            BasePipelineConfig(
                PIPELINE_TYPE=PipelineTypeEnum.PROCESSING,
                NAME="fmriprep",
                VERSION="24.1.1",
                SCHEMA_VERSION="1",
            ),
            {
                "keywords": [
                    "Nipoppy",
                    "pipeline_type:processing",
                    "pipeline_name:fmriprep",
                    "pipeline_version:24.1.1",
                    "schema_version:1",
                ]
            },
            True,
        ),
        (
            BasePipelineConfig(
                PIPELINE_TYPE=PipelineTypeEnum.PROCESSING,
                NAME="mriqc",
                VERSION="23.1.0",
                SCHEMA_VERSION="1",
            ),
            {
                "keywords": [
                    "Nipoppy",
                    "pipeline_type:processing",
                    "pipeline_name:fmriprep",
                    "pipeline_version:24.1.1",
                    "schema_version:1",
                ]
            },
            False,
        ),
        (
            BasePipelineConfig(
                PIPELINE_TYPE=PipelineTypeEnum.PROCESSING,
                NAME="FMRIPREP",
                VERSION="24.1.1",
                SCHEMA_VERSION="1",
            ),
            {
                "keywords": [
                    "Nipoppy",
                    "pipeline_type:processing",
                    "pipeline_name:fmriprep",
                    "pipeline_version:24.1.1",
                    "schema_version:1",
                ]
            },
            True,
        ),
    ],
)
def test_is_same_pipeline(pipeline_config, zenodo_metadata, expected):
    assert _is_same_pipeline(pipeline_config, zenodo_metadata) == expected


@pytest.mark.parametrize("force", [True, False])
def test_upload_same_pipeline(
    force: bool, zenodo_api_mocker: pytest_mock.MockerFixture
):
    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,  # fMRIprep 24.1.1
        zenodo_api=zenodo_api,
        record_id="1234567",
        assume_yes=True,
        force=force,
    )

    # Mock current pipeline metadata on Zenodo
    get_record_metadata = zenodo_api_mocker.patch.object(
        workflow.zenodo_api, "get_record_metadata"
    )
    # Mismatched pipeline metadata
    get_record_metadata.return_value = {
        "keywords": [
            "Nipoppy",
            "pipeline_type:processing",
            "pipeline_name:mriqc",
            "pipeline_version:23.1.0",
            "schema_version:1",
        ]
    }

    # Fails if force is False
    with (
        nullcontext()
        if force
        else pytest.raises(
            ZenodoAPIError,
            match="The pipeline metadata does not match the existing record",
        )
    ):
        workflow.run()


def test_confirm_upload_no(
    zenodo_api_mocker: pytest_mock.MockerFixture, caplog: pytest.LogCaptureFixture
):
    zenodo_api_mocker.patch(
        "nipoppy.workflows.pipeline_store.zenodo.CONSOLE_STDOUT.confirm",
        return_value=False,
    )
    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline="not_used",
        zenodo_api=zenodo_api,
        assume_yes=False,
    )

    with pytest.raises(SystemExit):
        workflow.run_main()

    assert "Zenodo upload cancelled." in caplog.text


@pytest.mark.parametrize(
    "hits, potential_duplicates",
    [
        [
            [
                {"links": {"self_html": "https://zenodo.org/records/123456"}},
                {"links": {"self_html": "https://zenodo.org/records/123456"}},
                {"links": {"self_html": "https://zenodo.org/records/123456"}},
            ],
            "https://zenodo.org/records/123456, https://zenodo.org/records/123456, https://zenodo.org/records/123456",
        ]
    ],
)
def test_upload_duplicate_record(
    hits: list,
    potential_duplicates: str,
    zenodo_api_mocker: pytest_mock.MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,  # fMRIprep 24.1.1
        zenodo_api=zenodo_api,
        assume_yes=True,
    )

    search_records = zenodo_api_mocker.patch.object(
        workflow.zenodo_api, "search_records"
    )
    search_records.return_value = {
        "hits": hits,
    }

    with pytest.raises(
        ZenodoAPIError,
        match="It looks like this pipeline already exists in Zenodo. Aborting.",
    ):
        workflow.run()
        assert potential_duplicates in caplog.text


def test_force_upload_duplicate_record(zenodo_api_mocker: pytest_mock.MockerFixture):
    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,  # fMRIprep 24.1.1
        zenodo_api=zenodo_api,
        assume_yes=True,
        force=True,
    )

    search_records = zenodo_api_mocker.patch.object(
        workflow.zenodo_api, "search_records"
    )
    search_records.return_value = {
        "hits": {"doi": "abc.123"},
    }

    workflow.run()
