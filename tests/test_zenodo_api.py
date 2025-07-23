"""Test for Zenodo API."""

import os
from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_httpx

from nipoppy.zenodo_api import InvalidChecksumError, ZenodoAPI, ZenodoAPIError

from .conftest import datetime_fixture  # noqa F401
from .conftest import PASSWORD_FILE, TEST_PIPELINE

ZENODO_SANDBOX = True


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


@pytest.fixture(scope="function")
def zenodo_api():
    """Fixture for Zenodo API."""
    return ZenodoAPI(sandbox=ZENODO_SANDBOX, password_file=PASSWORD_FILE)


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


@pytest.mark.parametrize(
    "content,expected_checksum, checksum_match",
    [
        ("abc", "900150983cd24fb0d6963f7d28e17f72", True),
        ("abc", "wrong_checksum", False),
    ],
)
def test_download_record_checksum(
    tmp_path: Path,
    zenodo_api: ZenodoAPI,
    content: str,
    expected_checksum,
    checksum_match,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"
    filename = "fake_file"
    httpx_mock.add_response(
        url=zenodo_api.api_endpoint + f"/records/{record_id}/files",
        method="GET",
        json={
            "entries": [
                {
                    "key": filename,
                    "checksum": expected_checksum,
                }
            ]
        },
    )
    httpx_mock.add_response(
        url=zenodo_api.api_endpoint + f"/records/{record_id}/files/{filename}/content",
        method="GET",
        content=content.encode(),
    )

    with (
        nullcontext()
        if checksum_match
        else pytest.raises(
            InvalidChecksumError, match="Checksum mismatch: .* has invalid checksum"
        )
    ):
        zenodo_api.download_record_files(output_dir=tmp_path, record_id=record_id)


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


def test_create_draft(zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock):
    # Set mock response
    metadata = {"metadata": dict()}
    httpx_mock.add_response(
        url=zenodo_api.api_endpoint + "/records",
        status_code=201,
        method="POST",
        json={"id": "123456", "owners": [{"id": "987"}]},
        match_headers={
            "Authorization": "Bearer mocked_api",
            "Content-Type": "application/json",
        },
        match_json=metadata,
    )

    # Assertions
    result = zenodo_api._create_draft(metadata)
    assert result == ("123456", "987")


def test_create_draft_fails(zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock):
    # Set mock response
    metadata = {"metadata": dict()}
    httpx_mock.add_response(
        url=zenodo_api.api_endpoint + "/records",
        method="POST",
        status_code=000,  # Failed status code
        json={"id": "123456"},
        match_headers={
            "Authorization": "Bearer mocked_api",
            "Content-Type": "application/json",
        },
    )

    # Assertions
    with pytest.raises(ZenodoAPIError, match="Failed to create a draft record:"):
        zenodo_api._create_draft(metadata)


@pytest.mark.parametrize(
    "json_response,expected_creators",
    [
        (
            {"profile": {}, "identities": {}, "username": "fake_user"},
            [
                {
                    "person_or_org": {
                        "family_name": "fake_user",
                        "identifiers": [],
                        "type": "personal",
                    },
                    "affiliations": [],
                }
            ],
        ),
        (
            {
                "profile": {
                    "full_name": "first_name last_name",
                    "affiliations": "Fake University",
                },
                "identities": {"orcid": "0000-0000-0000-0000"},
                "username": "fake_user",
            },
            [
                {
                    "person_or_org": {
                        "family_name": "first_name last_name",
                        "identifiers": [
                            {"identifier": "0000-0000-0000-0000", "scheme": "orcid"}
                        ],
                        "type": "personal",
                    },
                    "affiliations": [{"name": "Fake University"}],
                }
            ],
        ),
    ],
)
def test_update_creators(
    json_response,
    expected_creators,
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"
    owner_id = "888888"
    metadata = {"metadata": {}}

    # mock the API
    httpx_mock.add_response(
        method="GET",
        url=zenodo_api.api_endpoint + f"/users/{owner_id}",
        json=json_response,
    )
    httpx_mock.add_response(
        url=zenodo_api.api_endpoint + f"/records/{record_id}/draft",
        method="PUT",
        match_json={"metadata": {"creators": expected_creators}},
    )

    zenodo_api._update_creators(record_id, owner_id, metadata)


def test_valid_authentication(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    httpx_mock.add_response(
        url=zenodo_api.api_endpoint + "/user/records",
        method="GET",
        status_code=200,
    )
    zenodo_api._check_authentication()


def test_failed_authentication(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    httpx_mock.add_response(
        url=zenodo_api.api_endpoint + "/user/records",
        method="GET",
        status_code=403,
        json={"status": 403, "message": "Permission denied."},
    )

    with pytest.raises(ZenodoAPIError, match="Failed to authenticate to Zenodo:"):
        zenodo_api._check_authentication()


@pytest.mark.api
@pytest.mark.parametrize("query", ["FMRIPREP", ""])
@pytest.mark.parametrize("keywords", [None, [], ["Nipoppy", "schema_version:1"]])
def test_search_records(query, keywords, zenodo_api: ZenodoAPI):
    # TODO search in official Zenodo instead of sandbox
    results = zenodo_api.search_records(query, keywords=keywords)
    assert len(results["hits"]) > 0
    assert results["total"] > 0


def test_search_records_api_call(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    search_query = "FMRIPREP"
    keyword = "Nipoppy"
    size = 100

    httpx_mock.add_response(
        url=zenodo_api.api_endpoint
        + "/records?q=FMRIPREP+AND+metadata.subjects.subject%3A%22Nipoppy%22&size=100",
        method="GET",
        json={"hits": {}},
    )
    zenodo_api.search_records(search_query, keywords=[keyword], size=size)


def test_search_records_error_size(zenodo_api: ZenodoAPI):
    with pytest.raises(
        ValueError,
        match="size must be greater than 0",
    ):
        # exits before actually making the API call
        zenodo_api.search_records(query="FMRIPREP", size=0)
