"""Client for Zenodo API."""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

import httpx

from nipoppy.logger import get_logger


class InvalidChecksumError(Exception):
    """Checksum mismatch between two files."""

    pass


class ZenodoAPIError(Exception):
    """Error when interacting with Zenodo API."""

    pass


class ZenodoAPI:
    """Client to interact with Zenodo API.

    Zenodo uses the InvenioRDM API, which is documented at:
    https://inveniordm.docs.cern.ch/reference/rest_api_index/
    """

    def __init__(
        self,
        sandbox: bool = False,
        access_token: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.api_endpoint = (
            "https://sandbox.zenodo.org/api" if sandbox else "https://zenodo.org/api"
        )
        self.access_token = access_token

        if logger is None:
            self.logger = get_logger(__name__)
        else:
            self.logger = logger

        # Access token is required for uploading files
        if self.access_token is not None:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
            }
        else:
            self.headers = {}

    def set_logger(self, logger: logging.Logger):
        """Set the logger for the ZenodoAPI instance."""
        self.logger = logger

    def download_record_files(self, record_id: str, output_dir: Path):
        """Download the files of a Zenodo record in the `output_dir` directory.

        Parameters
        ----------
        record_id : str
            Record ID in Zenodo.
        output_dir : Path
            Output directory to save the files.

        Raises
        ------
        InvalidChecksumError
            Checksum mismatch between the downloaded file and the expected checksum.
        """
        record_id = record_id.removeprefix("zenodo.")
        output_dir.mkdir(parents=True, exist_ok=True)

        response = httpx.get(
            f"{self.api_endpoint}/records/{record_id}/files",
            headers=self.headers,
        )
        if response.status_code != 200:
            raise ZenodoAPIError(
                f"Failed to get files for zenodo.{record_id}: {response.json()}"
            )

        # Exclude "md5:" prefix
        files = {
            entry["key"]: entry["checksum"].removeprefix("md5:")
            for entry in response.json()["entries"]
        }
        for file, checksum in files.items():
            response = httpx.get(
                f"{self.api_endpoint}/records/{record_id}/files/{file}/content",  # noqa E501
                headers=self.headers,
            )
            if response.status_code != 200:
                raise ZenodoAPIError(
                    f"Failed to download file for zenodo.{record_id}: {file}"
                    f"\n{response.json()}"
                )

            # Checksum verification before writing to disk
            content_md5 = hashlib.md5(response.content).hexdigest()
            if content_md5 != checksum:
                raise InvalidChecksumError(
                    "Checksum mismatch: " f"'{file}' has invalid checksum {content_md5}"
                )

            output_dir.joinpath(file).write_bytes(response.content)

    def _create_new_version(self, record_id: str, metadata: dict) -> Tuple[str, str]:
        response = httpx.post(
            f"{self.api_endpoint}/records/{record_id}/versions",
            headers=self.headers,
        )
        if response.status_code != 201:
            raise ZenodoAPIError(
                f"Failed to create a new version for zenodo.{record_id}:"
                f" {response.json()}"
            )
        new_record_id = response.json()["id"]
        owner_id = response.json()["owners"][0]["id"]

        # Required to update the metadata to include the new publication date
        response = httpx.put(
            f"{self.api_endpoint}/records/{new_record_id}/draft",
            headers=self.headers,
            json=metadata,
        )
        if response.status_code != 200:
            raise ZenodoAPIError(
                f"Failed to update metadata for zenodo.{record_id}: {response.json()}"
            )

        return new_record_id, owner_id

    def _create_draft(self, metadata: dict) -> Tuple[str, str]:
        response = httpx.post(
            f"{self.api_endpoint}/records",
            headers=self.headers | {"Content-Type": "application/json"},
            json=metadata,
        )
        if response.status_code != 201:
            raise ZenodoAPIError(f"Failed to create a draft record: {response.json()}")

        return response.json()["id"], response.json()["owners"][0]["id"]

    def _update_creators(self, record_id: str, owner_id: str, metadata: dict):
        # get user profile info
        response = httpx.get(
            f"{self.api_endpoint}/users/{owner_id}", headers=self.headers
        )
        if response.status_code != 200:
            raise ZenodoAPIError(
                f"Failed to get information for user {owner_id}: {response.json()}"
            )

        # extract creator name
        # use username (always defined) as fallback
        response_json = response.json()
        if (creator_name := response_json["profile"]["full_name"]) == "":
            creator_name = response_json["username"]
            self.logger.warning(
                f"User {owner_id} has no full name in Zenodo profile, "
                f'using username ("{creator_name}") instead'
            )
        # also get affiliation and ORCID (may be empty)
        affiliation = response_json["profile"]["affiliations"]
        orcid = response_json["identities"].get("orcid")

        # update metadata with new creator information
        metadata["metadata"]["creators"] = [
            {
                "person_or_org": {
                    "family_name": creator_name,
                    "identifiers": (
                        [{"identifier": orcid, "scheme": "orcid"}] if orcid else []
                    ),
                    "type": "personal",
                },
                "affiliations": [{"name": affiliation}] if affiliation else [],
            }
        ]
        response = httpx.put(
            f"{self.api_endpoint}/records/{record_id}/draft",
            headers=self.headers,
            json=metadata,
        )
        if response.status_code != 200:
            raise ZenodoAPIError(
                f"Failed to update metadata for zenodo.{record_id}: {response.json()}"
            )

    def _upload_files(self, files: list[Path], record_id: str):
        metadata = [{"key": file.name} for file in files]
        response = httpx.post(
            f"{self.api_endpoint}/records/{record_id}/draft/files",
            headers=self.headers | {"Content-Type": "application/json"},
            json=metadata,
        )
        if response.status_code != 201:
            raise ZenodoAPIError(
                f"Failed to create upload file list for zenodo.{record_id}: {files}"
                f"\n{response.json()}"
            )

        for file in files:
            # Upload the file content
            with file.open("rb") as f:
                response = httpx.put(
                    f"{self.api_endpoint}/records/{record_id}/draft/files/{file.name}/content",  # noqa E501
                    headers=self.headers | {"Content-Type": "application/octet-stream"},
                    content=f,
                )
                if response.status_code != 200:
                    raise ZenodoAPIError(
                        f"Failed to upload file for zenodo.{record_id}: {file.name}"
                        f"\n{response.json()}"
                    )

            # Commit the uploaded file
            response = httpx.post(
                f"{self.api_endpoint}/records/{record_id}/draft/files/{file.name}/commit",  # noqa E501
                headers=self.headers,
            )
            if response.status_code != 200:
                raise ZenodoAPIError(
                    f"Failed to commit the file file for zenodo.{record_id}: {file}"
                    f"\n{response.json()}"
                )

    def _publish(self, record_id: str) -> str:
        response = httpx.post(
            f"{self.api_endpoint}/records/{record_id}/draft/actions/publish",
            headers=self.headers,
        )
        if response.status_code != 202:
            raise ZenodoAPIError(
                (f"Failed to publish zenodo.{record_id}: {response.json()}")
            )

        return response.json()["links"]["self_doi"]

    def _check_authentication(self) -> None:
        response = httpx.get(
            f"{self.api_endpoint}/user/records",
            headers=self.headers | {"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            raise ZenodoAPIError(f"Failed to authenticate to Zenodo: {response.json()}")

    def upload_pipeline(
        self,
        input_dir: Path,
        metadata: dict,
        record_id: Optional[str] = None,
    ) -> str:
        """Upload a pipeline to Zenodo."""
        record_id = record_id.removeprefix("zenodo.") if record_id else None
        if not input_dir.exists():
            raise FileNotFoundError(input_dir)
        if not input_dir.is_dir():
            raise ValueError(f"{input_dir} must be a directory.")

        self._check_authentication()

        if record_id:
            record_id, owner_id = self._create_new_version(record_id, metadata)
            action = "update"
        else:
            record_id, owner_id = self._create_draft(metadata)
            action = "creation"

        try:
            if not metadata["metadata"].get("creators"):
                self._update_creators(record_id, owner_id, metadata)

            files = list(input_dir.iterdir())
            self._upload_files(files, record_id)
            doi = self._publish(record_id)
            return doi

        except Exception:
            # Delete the draft if an error occurs
            # Prevents issue when retrying to modify the record while a draft exits.
            self.logger.warning(f"Reverting record {action} for zenodo.{record_id}")
            response = httpx.delete(
                f"{self.api_endpoint}/records/{record_id}/draft",
                headers=self.headers,
            )
            if response.status_code != 204:
                self.logger.warning(
                    f"Failed to revert record {action} for zenodo.{record_id}: "
                    f"{response.json()}"
                )

            raise SystemExit(1)

    def search_records(
        self,
        query: str,
        keywords: Optional[list[str]] = None,
        size: int = 10,
    ):
        """Search for records in Zenodo."""
        if size < 1:
            raise ValueError(f"size must be greater than 0, got {size}.")

        if keywords is None:
            keywords = []

        full_query = query
        for keyword in keywords:
            full_query += f" AND metadata.subjects.subject:{keyword}"
        # handle case where initial query is empty
        full_query = full_query.strip().removeprefix("AND ")

        self.logger.debug(f'Using Zenodo query string: "{full_query}"')

        response = httpx.get(
            f"{self.api_endpoint}/records",
            headers=self.headers,
            params={
                "q": full_query,
                "size": size,
            },
        )

        return response.json()["hits"]
