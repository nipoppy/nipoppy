"""Test for Zenodo API."""

from pathlib import Path
import os

import pytest
import pytest_mock

from nipoppy.zenodo import ZenodoAPI, ZenodoAPIError
from .conftest import DPATH_TEST_DATA, datetime_fixture

API_ENDPOINT = "https://sandbox.zenodo.org/api"


@pytest.fixture(scope="function")
def zenodo_id():
    """Fixture for Zenodo ID.

    The Sandbox can be reset at any time, so the Zenodo ID may change.
    If the test fails verify the Zenodo record at:
    https://sandbox.zenodo.org/records/170588

    The test file is located at: nipoppy/tests/data/zenodo.zip
    """
    return "170588"


@pytest.mark.parametrize("zenodo_id_prefix", ["", "zenodo."])
def test_download_record_files(tmp_path: Path, zenodo_id: str, zenodo_id_prefix: str):
    """Test for downloading a pipeline from Zenodo."""
    zenodo_id = zenodo_id_prefix + zenodo_id
    ZenodoAPI(api_endpoint=API_ENDPOINT).download_record_files(zenodo_id, tmp_path)

    assert len(list(tmp_path.iterdir())) == 2

    assert tmp_path.joinpath("zenodo-test.txt").read_text() == "test 123"
    assert tmp_path.joinpath("test2.txt").read_text() == "test2"


def test_download_invalid_record(tmp_path: Path):
    """Test for downloading an invalid pipeline from Zenodo."""
    zenodo_id = "invalid_record_id"

    with pytest.raises(
        ZenodoAPIError,
        match=(
            f"Failed to get files for zenodo.{zenodo_id}: "
            "{'status': 404, 'message': 'The persistent identifier does not exist.'}"
        ),
    ):
        ZenodoAPI(api_endpoint=API_ENDPOINT).download_record_files(zenodo_id, tmp_path)


@pytest.mark.skipif(
    os.environ.get("ZENODO_TOKEN") is None or os.environ.get("ZENODO_ID") is None,
    reason="Requires Zenodo token and ID",
)
def test_create_new_version():
    ZenodoAPI(
        api_endpoint=API_ENDPOINT, access_token=os.environ["ZENODO_TOKEN"]
    ).upload_pipeline(
        input_dir=DPATH_TEST_DATA / "pipeline_example" / "fmriprep-24.1.1",
        zenodo_id=os.environ["ZENODO_ID"],
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

    result = ZenodoAPI(
        api_endpoint=API_ENDPOINT, access_token="mocked_api"
    )._create_draft(metadata)

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
        ZenodoAPI(api_endpoint=API_ENDPOINT, access_token="mocked_api")._create_draft(
            metadata
        )

    mock_post.assert_called_once_with(url, json=metadata, headers=headers)


def test_valid_authentication(mocker: pytest_mock.MockerFixture):
    mocker.patch("httpx.get", return_value=mocker.Mock(status_code=200))

    ZenodoAPI(
        api_endpoint=API_ENDPOINT, access_token="valid_token"
    )._check_authetication()


def test_failed_authentication():
    with pytest.raises(ZenodoAPIError, match="Failed to authenticate to Zenodo:"):
        ZenodoAPI(
            api_endpoint=API_ENDPOINT, access_token="invalid_token"
        )._check_authetication()


def test_get_pipeline_metadata(tmp_path: Path, datetime_fixture):
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
            "keywords": ["Nipoppy"],
        }
    }

    assert expected == ZenodoAPI(api_endpoint=API_ENDPOINT)._get_pipeline_metadata(
        DPATH_TEST_DATA / "pipeline_example" / "fmriprep-24.1.1"
    )
