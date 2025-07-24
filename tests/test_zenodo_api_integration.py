import os
from pathlib import Path

import pytest

from nipoppy.zenodo_api import ZenodoAPI, ZenodoAPIError

from .conftest import datetime_fixture  # noqa F401
from .conftest import TEST_PIPELINE

ZENODO_SANDBOX = True


@pytest.fixture(scope="function")
def zenodo_api():
    """Fixture for Zenodo API."""
    return ZenodoAPI(sandbox=ZENODO_SANDBOX)


@pytest.fixture(scope="function")
def metadata():
    """Zenodo metadata fixture for uploads."""
    return {
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


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_ID")),
    reason="Requires Zenodo record ID",
)
@pytest.mark.parametrize("record_id_prefix", ["", "zenodo."])
def test_download_record_files(
    tmp_path: Path, zenodo_api: ZenodoAPI, record_id_prefix: str
):
    """Test for downloading a pipeline from Zenodo."""
    record_id = record_id_prefix + os.environ["ZENODO_ID"]
    zenodo_api.download_record_files(record_id, tmp_path)

    assert len(list(tmp_path.iterdir())) == 6

    # Verify the content of the downloaded files
    for file in TEST_PIPELINE.iterdir():
        assert tmp_path.joinpath(file.name).exists()
        assert tmp_path.joinpath(file.name).read_text() == file.read_text()


@pytest.mark.api
def test_download_invalid_record(tmp_path: Path, zenodo_api: ZenodoAPI):
    """Test for downloading an invalid pipeline from Zenodo."""
    record_id = "invalid_record_id"

    with pytest.raises(
        ZenodoAPIError,
        match=(
            f"Failed to get files for zenodo.{record_id}: "
            "{'status': 404, 'message': 'The persistent identifier does not exist.'}"
        ),
    ):
        zenodo_api.download_record_files(record_id, tmp_path)


@pytest.mark.api
@pytest.mark.skipif(
    (not (os.environ.get("ZENODO_TOKEN") and os.environ.get("ZENODO_ID"))),
    reason="Requires Zenodo token and record ID",
)
def test_create_new_version(zenodo_api: ZenodoAPI, metadata: dict):
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])
    zenodo_api.upload_pipeline(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        record_id=os.environ["ZENODO_ID"],
    )


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_TOKEN")),
    reason="Requires Zenodo token",
)
def test_create_new_version_invalid_record(zenodo_api: ZenodoAPI, metadata: dict):
    record_id = "invalid_record_id"
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])

    with pytest.raises(
        ZenodoAPIError,
        match=(
            f"Failed to create a new version for zenodo.{record_id}: "
            "{'status': 404, 'message': 'The persistent identifier does not exist.'}"
        ),
    ):
        zenodo_api.upload_pipeline(
            input_dir=TEST_PIPELINE,
            metadata=metadata,
            record_id=record_id,
        )


@pytest.mark.api
@pytest.mark.skipif(
    not os.environ.get("ZENODO_TOKEN"),
    reason="Requires Zenodo token",
)
def test_create_new_record(zenodo_api: ZenodoAPI, metadata: dict):
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])
    zenodo_api.upload_pipeline(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
    )


@pytest.mark.api
def test_create_new_record_invalid_token(zenodo_api: ZenodoAPI, metadata: dict):
    zenodo_api.set_authorization("invalid_token")

    with pytest.raises(
        ZenodoAPIError,
        match=(
            "Failed to authenticate to Zenodo: "
            "{'status': 403, 'message': 'Permission denied.'}"
        ),
    ):
        zenodo_api.upload_pipeline(
            input_dir=TEST_PIPELINE,
            metadata=metadata,
        )


@pytest.mark.api
@pytest.mark.parametrize("query", ["FMRIPREP", ""])
@pytest.mark.parametrize("keywords", [None, ["Nipoppy", "schema_version:1"]])
def test_search_records(query, keywords, zenodo_api: ZenodoAPI):
    results = zenodo_api.search_records(query, keywords=keywords)
    assert len(results["hits"]) > 0
    assert results["total"] > 0
