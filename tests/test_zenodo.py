"""Test for Zenodo API."""

from pathlib import Path

import pytest

from nipoppy.zenodo import ZenodoAPI

API_ENDPOINT = "https://sandbox.zenodo.org/api"


@pytest.fixture(scope="function")
def zenodo_id():
    """Fixture for Zenodo ID.

    The Sandbox can be reset at any time, so the Zenodo ID may change.
    If the test fails verify the Zenodo record at:
    https://sandbox.zenodo.org/records/170588
    """
    return "170588"


@pytest.mark.parametrize("zenodo_id_prefix", ["", "zenodo."])
def test_download_record_files(tmp_path: Path, zenodo_id: str, zenodo_id_prefix: str):
    """Test for downloading a pipeline from Zenodo."""
    zenodo = ZenodoAPI(api_endpoint=API_ENDPOINT)

    zenodo_id = zenodo_id_prefix + zenodo_id
    zenodo.download_record_files(zenodo_id, tmp_path)

    assert len(list(tmp_path.iterdir())) == 2

    assert tmp_path.joinpath("zenodo-test.txt").read_text() == "test 123"
    assert tmp_path.joinpath("test2.txt").read_text() == "test2"
