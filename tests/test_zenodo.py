"""Test for Zenodo API."""

from pathlib import Path

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


def test_create_new_version():
    
    pass


def test_create_draft():

    pass


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
