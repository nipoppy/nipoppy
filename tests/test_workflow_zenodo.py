import pytest_mock

from nipoppy.pipeline_store.validation import _load_pipeline_config_file
from nipoppy.workflows.pipeline_store.zenodo import (
    ZenodoUploadWorkflow,
)
from nipoppy.zenodo_api import ZenodoAPI

from .conftest import TEST_PIPELINE

DATASET_PATH = "my_dataset"


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
    )
    workflow.run_main()

    upload_pipeline.assert_called_once()
    get_pipeline_metadata.assert_called_once()
    validator.assert_called_once()


def test_get_pipeline_metadata(
    datetime_fixture,
):  # noqa F811
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
            "keywords": ["Nipoppy", "processing"],
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
    # Convert keywords to set to prevent order mismatch
    results["metadata"]["keywords"] = set(results["metadata"]["keywords"])
    expected["metadata"]["keywords"] = set(expected["metadata"]["keywords"])

    assert results == expected
