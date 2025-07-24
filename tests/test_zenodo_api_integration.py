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
    return ZenodoAPI(sandbox=ZENODO_SANDBOX)  # TODO is password needed here?


@pytest.fixture(scope="function")
def record_id():
    """Fixture for Zenodo ID.

    The Sandbox can be reset at any time, so the Zenodo ID may change.
    If the test fails verify the Zenodo record at:
    https://sandbox.zenodo.org/records/{record_id}

    See TEST_PIPELINE for test file location.
    """
    return "213135"


@pytest.fixture(scope="function")
def metadata():
    """Fixture for Zenodo metadata."""
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
@pytest.mark.parametrize("record_id_prefix", ["", "zenodo."])
def test_download_record_files(
    tmp_path: Path, zenodo_api: ZenodoAPI, record_id: str, record_id_prefix: str
):
    """Test for downloading a pipeline from Zenodo."""
    record_id = record_id_prefix + record_id
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
    os.environ.get("ZENODO_TOKEN") is None
    or os.environ.get("ZENODO_TOKEN") == ""
    or os.environ.get("ZENODO_ID") is None,
    reason="Requires Zenodo token and ID",
)
@pytest.mark.parametrize("prefix", ["", "zenodo."])
def test_create_new_version(prefix: str, metadata: dict):
    api = ZenodoAPI(sandbox=ZENODO_SANDBOX)
    api.set_authorization(os.environ["ZENODO_TOKEN"])
    api.upload_pipeline(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        record_id=f"{prefix}{os.environ['ZENODO_ID']}",
    )


@pytest.mark.api
@pytest.mark.parametrize("query", ["FMRIPREP", ""])
@pytest.mark.parametrize("keywords", [None, [], ["Nipoppy", "schema_version:1"]])
def test_search_records(query, keywords, zenodo_api: ZenodoAPI):
    # TODO search in official Zenodo instead of sandbox
    results = zenodo_api.search_records(query, keywords=keywords)
    assert len(results["hits"]) > 0
    assert results["total"] > 0
