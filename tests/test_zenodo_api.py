"""Test for Zenodo API."""

import os
from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.zenodo_api import InvalidChecksumError, ZenodoAPI, ZenodoAPIError

from .conftest import TEST_PIPELINE, datetime_fixture  # noqa F401

ZENODO_SANDBOX = True


@pytest.fixture(scope="function")
def record_id():
    """Fixture for Zenodo ID.

    The Sandbox can be reset at any time, so the Zenodo ID may change.
    If the test fails verify the Zenodo record at:
    https://sandbox.zenodo.org/records/194256

    See TEST_PIPELINE for test file location.
    """
    return "199318"


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
    return ZenodoAPI(sandbox=ZENODO_SANDBOX)


@pytest.mark.parametrize("record_id_prefix", ["", "zenodo."])
def test_download_record_files(
    tmp_path: Path, zenodo_api: ZenodoAPI, record_id: str, record_id_prefix: str
):
    """Test for downloading a pipeline from Zenodo."""
    record_id = record_id_prefix + record_id
    zenodo_api.download_record_files(record_id, tmp_path)

    assert len(list(tmp_path.iterdir())) == 5

    # Verify the content of the downloaded files
    for file in TEST_PIPELINE.iterdir():
        assert tmp_path.joinpath(file.name).exists()
        assert tmp_path.joinpath(file.name).read_text() == file.read_text()


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
    content,
    expected_checksum,
    checksum_match,
    mocker: pytest_mock.MockerFixture,
):
    mock_post = mocker.patch("httpx.get")
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = content.encode()
    mock_response.json.return_value = {
        "entries": [
            {
                "key": "not_used",
                "checksum": expected_checksum,
            }
        ]
    }
    mock_post.return_value = mock_response

    with (
        nullcontext()
        if checksum_match
        else pytest.raises(
            InvalidChecksumError, match="Checksum mismatch: .* has invalid checksum"
        )
    ):
        zenodo_api.download_record_files(output_dir=tmp_path, record_id="123456")


@pytest.mark.skipif(
    os.environ.get("ZENODO_TOKEN") is None
    or os.environ.get("ZENODO_TOKEN") == ""
    or os.environ.get("ZENODO_ID") is None,
    reason="Requires Zenodo token and ID",
)
@pytest.mark.parametrize("prefix", ["", "zenodo."])
def test_create_new_version(prefix: str, metadata: dict):
    ZenodoAPI(
        sandbox=ZENODO_SANDBOX, access_token=os.environ["ZENODO_TOKEN"]
    ).upload_pipeline(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        record_id=f"{prefix}{os.environ['ZENODO_ID']}",
    )


def test_create_draft(mocker: pytest_mock.MockerFixture):
    # Set mock response
    mock_post = mocker.patch("httpx.post")
    mock_response = mocker.Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "123456", "owners": [{"id": "987"}]}
    mock_post.return_value = mock_response

    # Call the function under test
    url = "https://sandbox.zenodo.org/api/records"
    headers = {
        "Authorization": "Bearer mocked_api",
        "Content-Type": "application/json",
    }
    metadata = {"metadata": dict()}

    result = ZenodoAPI(sandbox=ZENODO_SANDBOX, access_token="mocked_api")._create_draft(
        metadata
    )

    # Assertions
    mock_post.assert_called_once_with(url, json=metadata, headers=headers)
    assert result == ("123456", "987")


def test_create_draft_fails(mocker: pytest_mock.MockerFixture):
    # Set mock response
    mock_post = mocker.patch("httpx.post")
    mock_response = mocker.Mock()
    mock_response.status_code = 000  # Failed status code
    mock_response.json.return_value = {"id": "123456"}
    mock_post.return_value = mock_response

    # Call the function under test
    url = "https://sandbox.zenodo.org/api/records"
    headers = {
        "Authorization": "Bearer mocked_api",
        "Content-Type": "application/json",
    }
    metadata = {"metadata": dict()}

    # Assertions
    with pytest.raises(ZenodoAPIError, match="Failed to create a draft record:"):
        ZenodoAPI(sandbox=ZENODO_SANDBOX, access_token="mocked_api")._create_draft(
            metadata
        )

    mock_post.assert_called_once_with(url, json=metadata, headers=headers)


def test_valid_authentication(mocker: pytest_mock.MockerFixture):
    mocker.patch("httpx.get", return_value=mocker.Mock(status_code=200))

    ZenodoAPI(sandbox=ZENODO_SANDBOX, access_token="mocked_api")._check_authentication()


def test_failed_authentication():
    with pytest.raises(ZenodoAPIError, match="Failed to authenticate to Zenodo:"):
        ZenodoAPI(
            sandbox=ZENODO_SANDBOX, access_token="invalid_token"
        )._check_authentication()


@pytest.mark.parametrize("query", ["FMRIPREP", ""])
@pytest.mark.parametrize("keywords", [None, []])
def test_search_records(query, keywords, zenodo_api: ZenodoAPI):
    # TODO search in official Zenodo instead of sandbox
    results = zenodo_api.search_records(query, keywords=keywords)
    assert len(results["hits"]) > 0
    assert results["total"] > 0


def test_search_records_api_call(
    zenodo_api: ZenodoAPI, mocker: pytest_mock.MockerFixture
):
    search_query = "FMRIPREP"
    keyword = "Nipoppy"
    size = 100

    mocked = mocker.patch("httpx.get")
    zenodo_api.search_records(search_query, keywords=[keyword], size=size)

    mocked.assert_called_once()

    params = mocked.call_args[1]["params"]
    assert search_query in params["q"]
    assert f"metadata.subjects.subject:{keyword}" in params["q"]
    assert params["size"] == size


def test_search_records_error_size(zenodo_api: ZenodoAPI):
    with pytest.raises(
        ValueError,
        match="size must be greater than 0",
    ):
        zenodo_api.search_records(query="FMRIPREP", size=0)
