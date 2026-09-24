import os
from pathlib import Path

import httpx
import pytest

from nipoppy.zenodo_api import ZenodoAPI, ZenodoAPIError

from ..conftest import (
    TEST_PIPELINE,
    datetime_fixture,  # noqa F401
)

ZENODO_SANDBOX = True
SANDBOX_COMMUNITY_ID = "6bea0505-4b7e-4340-93a4-8275e747748e"
DEFAULT_PREVIEW = "config.json"


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

    expected_files = list(TEST_PIPELINE.iterdir())
    assert len(list(tmp_path.iterdir())) == len(expected_files)

    # Verify the content of the downloaded files
    for file in expected_files:
        assert tmp_path.joinpath(file.name).exists()
        assert tmp_path.joinpath(file.name).read_text() == file.read_text()


@pytest.mark.api
def test_download_invalid_record(tmp_path: Path, zenodo_api: ZenodoAPI):
    """Test for downloading an invalid pipeline from Zenodo."""
    record_id = "invalid_record_id"

    with pytest.raises(
        ZenodoAPIError,
        match=(
            f"Failed to get record for zenodo.{record_id}: "
            "{'status': 404, 'message': 'The persistent identifier does not exist.'}"
        ),
    ):
        zenodo_api.download_record_files(record_id, tmp_path)


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_TOKEN")),
    reason="Requires Zenodo token",
)
def test_delete_draft(zenodo_api: ZenodoAPI):
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])

    # Create an unpublished draft
    draft_record_id, _ = zenodo_api._create_draft()
    assert zenodo_api.client.get(f"/records/{draft_record_id}/draft").status_code == 200

    # Delete it
    assert zenodo_api._delete_draft(draft_record_id) is None
    assert zenodo_api.client.get(f"/records/{draft_record_id}/draft").status_code == 404


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_TOKEN")),
    reason="Requires Zenodo token",
)
def test_delete_draft_not_found(zenodo_api: ZenodoAPI):
    """Test that _delete_draft is a no-op when the draft does not exist."""
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])

    draft_record_id = "invalid_record_id"

    assert zenodo_api.client.get(f"/records/{draft_record_id}/draft").status_code == 404
    assert zenodo_api._delete_draft(draft_record_id) is None


@pytest.mark.api
@pytest.mark.skipif(
    not os.environ.get("ZENODO_TOKEN"),
    reason="Requires Zenodo token",
)
def test_upload_record(zenodo_api: ZenodoAPI, metadata: dict):
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])
    doi = zenodo_api.upload_record(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        default_preview_filename=DEFAULT_PREVIEW,
    )

    # extract the new record ID from the DOI (e.g. 10.5072/zenodo.123456)
    new_record_id = doi.split("/")[-1].removeprefix("zenodo.")

    # verify that the default preview file is set correctly
    response = httpx.get(f"{zenodo_api.api_endpoint}/records/{new_record_id}/files")
    assert response.json()["default_preview"] == DEFAULT_PREVIEW


@pytest.mark.api
def test_upload_record_fails_with_invalid_token(zenodo_api: ZenodoAPI, metadata: dict):
    zenodo_api.set_authorization("invalid_token")

    with pytest.raises(
        ZenodoAPIError,
        match=(
            "Failed to authenticate to Zenodo: "
            "{'status': 403, 'message': 'Permission denied.'}"
        ),
    ):
        zenodo_api.upload_record(
            input_dir=TEST_PIPELINE,
            metadata=metadata,
        )


@pytest.mark.api
@pytest.mark.skipif(
    (not (os.environ.get("ZENODO_TOKEN") and os.environ.get("ZENODO_ID"))),
    reason="Requires Zenodo token and record ID",
)
def test_upload_record_with_existing_record_id(zenodo_api: ZenodoAPI, metadata: dict):
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])
    zenodo_api.upload_record(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        record_id=os.environ["ZENODO_ID"],
        default_preview_filename=DEFAULT_PREVIEW,
    )


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_TOKEN")),
    reason="Requires Zenodo token",
)
def test_upload_record_fails_with_invalid_record_id(
    zenodo_api: ZenodoAPI, metadata: dict
):
    record_id = "invalid_record_id"
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])

    with pytest.raises(
        ZenodoAPIError,
        match=(
            f"Failed to get latest version for zenodo.{record_id}: "
            "{'status': 404, 'message': 'The persistent identifier does not exist.'}"
        ),
    ):
        zenodo_api.upload_record(
            input_dir=TEST_PIPELINE,
            metadata=metadata,
            record_id=record_id,
        )


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_TOKEN")),
    reason="Requires Zenodo token",
)
def test_upload_record_cleans_up_after_failed_update(
    zenodo_api: ZenodoAPI, metadata: dict
):
    """Test that a failed update deletes the leftover draft and unblocks the record."""
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])

    # Create a fresh published record
    doi = zenodo_api.upload_record(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        default_preview_filename=DEFAULT_PREVIEW,
    )
    record_id = doi.split("/")[-1].removeprefix("zenodo.")

    # Leave a new version draft unpublished and populate it with files
    draft_record_id = zenodo_api._create_new_version(record_id)[0]
    assert draft_record_id != record_id
    zenodo_api._upload_files(sorted(TEST_PIPELINE.iterdir()), draft_record_id)

    # The update fails because the leftover draft is reused and
    # already contains the files
    with pytest.raises(
        ZenodoAPIError,
        match="Failed to update the Zenodo record",
    ):
        zenodo_api.upload_record(
            input_dir=TEST_PIPELINE,
            metadata=metadata,
            record_id=record_id,
            default_preview_filename=DEFAULT_PREVIEW,
        )

    # check that the leftover draft was deleted by the failed update
    assert zenodo_api.client.get(f"/records/{draft_record_id}/draft").status_code == 404
    assert zenodo_api.get_latest_version_id(record_id) == record_id

    # The record can be updated again
    new_doi = zenodo_api.upload_record(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        record_id=record_id,
        default_preview_filename=DEFAULT_PREVIEW,
    )
    assert new_doi.split("/")[-1].removeprefix("zenodo.") != record_id


@pytest.mark.api
@pytest.mark.parametrize("query", ["FMRIPREP", ""])
@pytest.mark.parametrize("keywords", [None, ["Nipoppy", "pipeline_type:processing"]])
def test_search_records(query, keywords, zenodo_api: ZenodoAPI):
    results = zenodo_api.search_records(query, keywords=keywords)
    assert len(results["hits"]) > 0
    assert results["total"] > 0


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_ID")),
    reason="Requires Zenodo record ID",
)
def test_get_latest_version_id(zenodo_api: ZenodoAPI):
    record_id = os.environ["ZENODO_ID"]
    assert zenodo_api.get_latest_version_id(record_id) != record_id


@pytest.mark.api
@pytest.mark.skipif(
    (not os.environ.get("ZENODO_ID")),
    reason="Requires Zenodo record ID",
)
def test_get_latest_version_id_invalid(zenodo_api: ZenodoAPI):
    record_id = "0"

    with pytest.raises(
        ZenodoAPIError,
        match=(
            f"Failed to get latest version for zenodo.{record_id}: "
            "{'status': 404, 'message': 'The persistent identifier does not exist.'}"
        ),
    ):
        zenodo_api.get_latest_version_id(record_id)


@pytest.mark.api
@pytest.mark.skipif(
    not os.environ.get("ZENODO_TOKEN"),
    reason="Requires Zenodo token",
)
def test_request_community_inclusion(zenodo_api: ZenodoAPI, metadata: dict):
    zenodo_api.set_authorization(os.environ["ZENODO_TOKEN"])
    doi = zenodo_api.upload_record(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        default_preview_filename=DEFAULT_PREVIEW,
    )

    new_record_id = doi.split("/")[-1].removeprefix("zenodo.")
    zenodo_api.request_community_inclusion(
        new_record_id, community_id=zenodo_api._get_community_id("nipoppy")
    )
    # Verify record opened a community request for inclusion in the Nipoppy community
    response = httpx.get(
        f"{zenodo_api.api_endpoint}/records/{new_record_id}/requests",
        headers=zenodo_api.client.headers,
    )
    response.raise_for_status()
    assert response.json()["hits"]["total"] == 1
    assert response.json()["hits"]["hits"][0]["type"] == "community-inclusion"
    assert response.json()["hits"]["hits"][0]["receiver"] == {
        "community": SANDBOX_COMMUNITY_ID
    }
