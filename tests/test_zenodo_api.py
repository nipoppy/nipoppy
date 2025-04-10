"""Test for Zenodo API."""

import os
from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.zenodo_api import InvalidChecksumError, ZenodoAPI, ZenodoAPIError

from .conftest import DPATH_TEST_DATA, datetime_fixture  # noqa F401

ZENODO_SANDBOX = True
TEST_PIPELINE = DPATH_TEST_DATA / "sample_pipelines" / "processing" / "fmriprep-24.1.1"


@pytest.fixture(scope="function")
def record_id():
    """Fixture for Zenodo ID.

    The Sandbox can be reset at any time, so the Zenodo ID may change.
    If the test fails verify the Zenodo record at:
    https://sandbox.zenodo.org/records/194256

    The test file is located at: tests/data/sample_pipelines/proc/fmriprep-24.1.1
    """
    return "194256"


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
def test_create_new_version(metadata: dict):
    ZenodoAPI(
        sandbox=ZENODO_SANDBOX, access_token=os.environ["ZENODO_TOKEN"]
    ).upload_pipeline(
        input_dir=TEST_PIPELINE,
        metadata=metadata,
        record_id=os.environ["ZENODO_ID"],
    )


def test_create_draft(mocker: pytest_mock.MockerFixture):
    # Set mock response
    mock_post = mocker.patch("httpx.post")
    mock_response = mocker.Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "123456"}
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
    assert result == "123456"


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
