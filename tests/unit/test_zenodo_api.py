"""Test for Zenodo API."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import pytest_httpx
import pytest_mock

from nipoppy.zenodo_api import ChecksumError, ZenodoAPI, ZenodoAPIError
from tests.conftest import PASSWORD_FILE


@pytest.fixture(scope="function")
def zenodo_api():
    """Fixture for Zenodo API."""
    return ZenodoAPI(sandbox=True, password_file=PASSWORD_FILE)


@pytest.mark.parametrize("logger", [None, logging.getLogger("test")])
def test_init_logger(logger):
    zenodo_api = ZenodoAPI(password_file=PASSWORD_FILE, logger=logger)
    assert isinstance(zenodo_api.logger, logging.Logger)


def test_download_record_files(
    tmp_path: Path, zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    record_id = "123456"
    filename = "abc.txt"
    content = "abc"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/files",
        method="GET",
        json={
            "entries": [
                {
                    "key": filename,
                    "checksum": "900150983cd24fb0d6963f7d28e17f72",
                }
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/files/{filename}/content",
        method="GET",
        content=content.encode(),
    )

    zenodo_api.download_record_files(output_dir=tmp_path, record_id=record_id)

    assert (tmp_path / filename).exists(), "File was not downloaded"
    assert (tmp_path / filename).read_text() == content, "File content does not match"


def test_download_record_files_invalid_record_id(
    tmp_path: Path, zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    record_id = "123456"
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/files",
        method="GET",
        status_code=404,
        json={"message": "The persistent identifier does not exist."},
    )

    with pytest.raises(
        ZenodoAPIError, match=f"Failed to get files for zenodo.{record_id}"
    ):
        zenodo_api.download_record_files(output_dir=tmp_path, record_id=record_id)


def test_download_record_files_download_failure(
    tmp_path: Path, zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    record_id = "123456"
    filename = "abc.txt"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/files",
        method="GET",
        json={
            "entries": [
                {
                    "key": filename,
                    "checksum": "900150983cd24fb0d6963f7d28e17f72",
                }
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/files/{filename}/content",
        method="GET",
        status_code=404,
        json={"message": "Error"},
    )

    with pytest.raises(
        ZenodoAPIError, match=f"Failed to download file for zenodo.{record_id}"
    ):
        zenodo_api.download_record_files(output_dir=tmp_path, record_id=record_id)


def test_download_record_files_checksum_mismatch(
    tmp_path: Path,
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"
    filename = "abc.txt"
    content = "abc"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/files",
        method="GET",
        json={
            "entries": [
                {
                    "key": filename,
                    "checksum": "wrong_checksum",
                }
            ]
        },
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/files/{filename}/content",
        method="GET",
        content=content.encode(),
    )

    with pytest.raises(
        ChecksumError, match="Checksum mismatch: .* has invalid checksum"
    ):
        zenodo_api.download_record_files(output_dir=tmp_path, record_id=record_id)


def test_create_new_version(zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock):
    record_id = "123456"
    new_record_id = "654321"
    owner_id = "888888"
    headers = {
        "Authorization": "Bearer mocked_api",
    }
    metadata = {"metadata": {}}

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/versions",
        method="POST",
        status_code=201,
        json={"id": new_record_id, "owners": [{"id": owner_id}]},
        match_headers=headers,
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{new_record_id}/draft",
        method="PUT",
        match_headers=headers,
        match_json=metadata,
    )

    assert zenodo_api._create_new_version(record_id=record_id, metadata=metadata) == (
        new_record_id,
        owner_id,
    )


def test_create_new_version_fails(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    record_id = "123456"
    headers = {
        "Authorization": "Bearer mocked_api",
    }
    metadata = {"metadata": {}}

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/versions",
        method="POST",
        status_code=500,
        json={},
        match_headers=headers,
    )

    with pytest.raises(
        ZenodoAPIError, match=f"Failed to create a new version for zenodo.{record_id}"
    ):
        zenodo_api._create_new_version(record_id=record_id, metadata=metadata)


def test_create_new_version_metadata_update_fails(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    record_id = "123456"
    new_record_id = "654321"
    owner_id = "888888"
    headers = {
        "Authorization": "Bearer mocked_api",
    }
    metadata = {"metadata": {}}

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/versions",
        method="POST",
        status_code=201,
        json={"id": new_record_id, "owners": [{"id": owner_id}]},
        match_headers=headers,
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{new_record_id}/draft",
        method="PUT",
        status_code=500,
        json={},
        match_headers=headers,
        match_json=metadata,
    )

    with pytest.raises(
        ZenodoAPIError,
        match=f"Failed to update metadata for zenodo.{record_id}",
    ):
        zenodo_api._create_new_version(record_id=record_id, metadata=metadata)


def test_create_draft(zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock):
    # Set mock response
    metadata = {"metadata": dict()}
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records",
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
        url=f"{zenodo_api.api_endpoint}/records",
        method="POST",
        status_code=500,
        json={},
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
        url=f"{zenodo_api.api_endpoint}/users/{owner_id}",
        json=json_response,
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft",
        method="PUT",
        match_json={"metadata": {"creators": expected_creators}},
    )

    zenodo_api._update_creators(record_id, owner_id, metadata)


def test_update_creators_invalid_id(
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"
    owner_id = "888888"
    metadata = {"metadata": {}}

    # mock the API
    httpx_mock.add_response(
        method="GET",
        url=f"{zenodo_api.api_endpoint}/users/{owner_id}",
        status_code=404,
        json={},
    )

    with pytest.raises(
        ZenodoAPIError,
        match=f"Failed to get information for user {owner_id}",
    ):
        zenodo_api._update_creators(record_id, owner_id, metadata)


def test_update_creators_metadata_update_fails(
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"
    owner_id = "888888"
    metadata = {"metadata": {}}

    # mock the API
    httpx_mock.add_response(
        method="GET",
        url=f"{zenodo_api.api_endpoint}/users/{owner_id}",
        json={"profile": {}, "identities": {}, "username": "fake_user"},
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft",
        method="PUT",
        status_code=500,
        json={},
    )

    with pytest.raises(
        ZenodoAPIError,
        match=f"Failed to update metadata for zenodo.{record_id}",
    ):
        zenodo_api._update_creators(record_id, owner_id, metadata)


@pytest.mark.parametrize(
    "filenames",
    [["abc.txt"], ["abc.txt", "def.txt"]],
)
def test_upload_files(
    filenames: list[str],
    tmp_path: Path,
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files",
        method="POST",
        status_code=201,
        match_headers={
            "Authorization": "Bearer mocked_api",
            "Content-Type": "application/json",
        },
        match_json=[{"key": filename} for filename in filenames],
    )
    for filename in filenames:
        (tmp_path / filename).write_text(filename)

        httpx_mock.add_response(
            url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files/{filename}/content",  # noqa: E501
            method="PUT",
            match_headers={
                "Authorization": "Bearer mocked_api",
                "Content-Type": "application/octet-stream",
            },
            match_content=filename.encode(),
        )
        httpx_mock.add_response(
            url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files/{filename}/commit",  # noqa: E501
            method="POST",
            match_headers={
                "Authorization": "Bearer mocked_api",
            },
        )

    zenodo_api._upload_files(
        files=[tmp_path / filename for filename in filenames],
        record_id=record_id,
    )


def test_upload_files_fails(
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files",
        method="POST",
        status_code=500,
        json={},
    )

    with pytest.raises(
        ZenodoAPIError,
        match=f"Failed to create upload file list for zenodo.{record_id}",
    ):
        zenodo_api._upload_files(files=[], record_id=record_id)


def test_upload_files_upload_fails(
    tmp_path: Path,
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"
    filename = "abc.txt"

    (tmp_path / filename).write_text(filename)

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files",
        method="POST",
        status_code=201,
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files/{filename}/content",  # noqa: E501
        method="PUT",
        status_code=500,
        json={},
    )

    with pytest.raises(
        ZenodoAPIError,
        match=f"Failed to upload file for zenodo.{record_id}",
    ):
        zenodo_api._upload_files(files=[tmp_path / filename], record_id=record_id)


def test_upload_files_commit_fails(
    tmp_path: Path,
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    record_id = "123456"
    filename = "abc.txt"

    (tmp_path / filename).write_text(filename)

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files",
        method="POST",
        status_code=201,
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files/{filename}/content",  # noqa: E501
        method="PUT",
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/files/{filename}/commit",  # noqa: E501
        method="POST",
        status_code=500,
        json={},
    )

    with pytest.raises(
        ZenodoAPIError,
        match=f"Failed to commit file for zenodo.{record_id}",
    ):
        zenodo_api._upload_files(files=[tmp_path / filename], record_id=record_id)


def test_publish(zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock):
    record_id = "123456"
    doi = "fake_doi"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/actions/publish",
        method="POST",
        match_headers={
            "Authorization": "Bearer mocked_api",
        },
        status_code=202,
        json={"links": {"self_doi": doi}},
    )

    assert zenodo_api._publish(record_id=record_id) == doi


def test_publish_fails(zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock):
    record_id = "123456"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft/actions/publish",
        method="POST",
        status_code=500,
        json={},
    )

    with pytest.raises(ZenodoAPIError, match=f"Failed to publish zenodo.{record_id}"):
        zenodo_api._publish(record_id=record_id)


def test_check_authentication(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/user/records",
        method="GET",
        status_code=200,
    )
    zenodo_api._check_authentication()


def test_check_authentication_fails(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/user/records",
        method="GET",
        status_code=403,
        json={},
    )

    with pytest.raises(ZenodoAPIError, match="Failed to authenticate to Zenodo:"):
        zenodo_api._check_authentication()


@pytest.mark.parametrize(
    "record_id,create_method_name",
    [
        ("123456", "_create_new_version"),
        ("zenodo.123456", "_create_new_version"),
        (None, "_create_draft"),
    ],
)
def test_upload_pipeline(
    record_id: str | None,
    create_method_name: str,
    tmp_path: Path,
    zenodo_api: ZenodoAPI,
    mocker: pytest_mock.MockerFixture,
):
    new_record_id = "654321"
    owner_id = "888888"
    metadata = {"metadata": {}}
    fnames = ["abc.txt", "def.txt"]
    doi = "fake_doi"

    for fname in fnames:
        (tmp_path / fname).write_text(fname)

    mocked_check_authentication = mocker.patch.object(
        zenodo_api, "_check_authentication"
    )
    mocked_create = mocker.patch.object(
        zenodo_api, create_method_name, return_value=(new_record_id, owner_id)
    )
    mocked_update_creators = mocker.patch.object(zenodo_api, "_update_creators")
    mocked_upload_files = mocker.patch.object(zenodo_api, "_upload_files")
    mocked_publish = mocker.patch.object(zenodo_api, "_publish", return_value=doi)

    assert (
        zenodo_api.upload_pipeline(
            input_dir=tmp_path, metadata=metadata, record_id=record_id
        )
        == doi
    )

    mocked_check_authentication.assert_called_once()
    mocked_create.assert_called_once()
    mocked_update_creators.assert_called_once_with(new_record_id, owner_id, metadata)
    mocked_upload_files.assert_called_once_with(
        [tmp_path / fname for fname in fnames], new_record_id
    )
    mocked_publish.assert_called_once_with(new_record_id)

    # last positional argument is metadata
    assert mocked_create.call_args[0][-1] == metadata


def test_upload_pipeline_custom_creators(
    tmp_path: Path, zenodo_api: ZenodoAPI, mocker: pytest_mock.MockerFixture
):
    mocker.patch.object(zenodo_api, "_check_authentication")
    mocker.patch.object(zenodo_api, "_create_draft", return_value=("654321", "888888"))
    mocked_update_creators = mocker.patch.object(zenodo_api, "_update_creators")
    mocker.patch.object(zenodo_api, "_upload_files")
    mocker.patch.object(zenodo_api, "_publish", return_value="fake_doi")

    zenodo_api.upload_pipeline(
        input_dir=tmp_path,
        metadata={
            "metadata": {
                "creators": [
                    {
                        "person_or_org": {
                            "given_name": "Test",
                            "family_name": "Test",
                            "type": "personal",
                        }
                    }
                ]
            }
        },
    )
    mocked_update_creators.assert_not_called()


def test_upload_pipeline_dir_not_found(zenodo_api: ZenodoAPI):
    with pytest.raises(FileNotFoundError):
        zenodo_api.upload_pipeline(input_dir=Path("fake_path"), metadata={})


def test_upload_pipeline_not_a_dir(tmp_path: Path, zenodo_api: ZenodoAPI):
    input_path = tmp_path / "file.txt"
    input_path.write_text("this is a file, not a directory")
    with pytest.raises(NotADirectoryError, match=f"{input_path} must be a directory"):
        zenodo_api.upload_pipeline(input_dir=input_path, metadata={})


@pytest.mark.parametrize(
    "delete_request_status_code,expected_log_message",
    [(204, "Record creation reverted"), (500, "Failed to revert record")],
)
@pytest.mark.no_xdist
def test_upload_pipeline_delete_draft(
    delete_request_status_code: int,
    expected_log_message: str,
    tmp_path: Path,
    zenodo_api: ZenodoAPI,
    mocker: pytest_mock.MockerFixture,
    httpx_mock: pytest_httpx.HTTPXMock,
    caplog: pytest.LogCaptureFixture,
):
    record_id = "123456"

    # mock functions/API calls
    mocker.patch.object(zenodo_api, "_check_authentication")
    mocker.patch.object(zenodo_api, "_create_draft", return_value=(record_id, "888888"))
    mocker.patch.object(zenodo_api, "_update_creators")
    mocker.patch.object(zenodo_api, "_upload_files")
    mocker.patch.object(
        zenodo_api, "_publish", side_effect=ZenodoAPIError("Publish failed")
    )
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}/draft",
        method="DELETE",
        status_code=delete_request_status_code,
        json={},
    )

    with pytest.raises(ZenodoAPIError):
        zenodo_api.upload_pipeline(
            input_dir=tmp_path,
            metadata={"metadata": {}},
        )

    assert "Reverting record creation" in caplog.text
    assert expected_log_message in caplog.text


@pytest.mark.parametrize(
    "search_query,keywords,size,sort,final_query",
    [
        (
            "FMRIPREP",
            None,
            100,
            "mostviewed",
            "%2AFMRIPREP%2A&size=100",
        ),
        (
            "fmriprep AND nipoppy",
            ["Nipoppy"],
            1,
            "mostdownloaded",
            "fmriprep+AND+nipoppy+AND+metadata.subjects.subject%3A%22Nipoppy%22&size=1",
        ),
    ],
)
def test_search_records(
    search_query,
    keywords,
    size,
    sort,
    final_query,
    zenodo_api: ZenodoAPI,
    httpx_mock: pytest_httpx.HTTPXMock,
):
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records?q={final_query}&sort={sort}",
        method="GET",
        json={"hits": {}},
    )
    zenodo_api.search_records(search_query, keywords=keywords, size=size, sort=sort)


def test_search_records_status_raised(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    # mock the response to have .raise_for_status() raise an error
    query = ""
    size = 10
    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records?q={query}&size={size}&sort=mostdownloaded",  # noqa: E501
        method="GET",
        status_code=500,
        json={},
    )
    with pytest.raises(
        ZenodoAPIError,
        match="Failed to search records. JSON response:",
    ):
        zenodo_api.search_records(query=query, size=size)


def test_search_records_wrong_size(zenodo_api: ZenodoAPI):
    with pytest.raises(
        ValueError,
        match="size must be greater than 0",
    ):
        # exits before actually making the API call
        zenodo_api.search_records(query="FMRIPREP", size=0)


@pytest.mark.parametrize(
    "community_id,expected_endpoint",
    [
        (None, "https://sandbox.zenodo.org/api/records"),
        ("", "https://sandbox.zenodo.org/api/records"),
        ("12345", "https://sandbox.zenodo.org/api/communities/12345/records"),
    ],
)
def test_get_api_endpoint(
    zenodo_api: ZenodoAPI, community_id: str, expected_endpoint: str
):
    assert zenodo_api._get_api_endpoint(community_id) == expected_endpoint


def test_get_record_metadata(zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock):
    record_id = "123456"
    metadata = {"title": "Test Title"}

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}",
        method="GET",
        json={"metadata": metadata},
    )

    assert zenodo_api.get_record_metadata(record_id=record_id) == metadata


def test_get_record_metadata_fails(
    zenodo_api: ZenodoAPI, httpx_mock: pytest_httpx.HTTPXMock
):
    record_id = "123456"

    httpx_mock.add_response(
        url=f"{zenodo_api.api_endpoint}/records/{record_id}",
        method="GET",
        status_code=500,
        json={},
    )

    with pytest.raises(
        ZenodoAPIError, match=f"Failed to get metadata for zenodo.{record_id}"
    ):
        zenodo_api.get_record_metadata(record_id=record_id)
