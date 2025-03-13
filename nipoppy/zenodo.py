"""Client for Zenodo API."""

import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx


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

    def __init__(self, api_endpoint: str, access_token: Optional[str] = None):
        self.api_endpoint = api_endpoint
        self.access_token = access_token

        if self.access_token is not None:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
            }
        else:
            self.headers = {}

    def download_record_files(self, zenodo_id: str, output_dir: Path):
        """Download the files of a Zenodo record in the `output_dir` directory.

        Parameters
        ----------
        zenodo_id : str
            Record ID in Zenodo.
        output_dir : Path
            Output directory to save the files.

        Raises
        ------
        InvalidChecksumError
            Checksum mismatch between the downloaded file and the expected checksum.
        """
        zenodo_id = zenodo_id.removeprefix("zenodo.")
        output_dir.mkdir(parents=True, exist_ok=True)

        response = httpx.get(
            f"{self.api_endpoint}/records/{zenodo_id}/files",
            headers=self.headers,
        )
        if response.status_code != 200:
            raise ZenodoAPIError(f"Failed to get files for zenodo.{zenodo_id}")

        # Exclude "md5:" prefix
        files = {
            entry["key"]: entry["checksum"].removeprefix("md5:")
            for entry in response.json()["entries"]
        }
        for filename, checksum in files.items():
            response = httpx.get(
                f"{self.api_endpoint}/records/{zenodo_id}/files/{filename}/content",  # noqa E501
                headers=self.headers,
            )
            if response.status_code != 200:
                raise ZenodoAPIError(
                    f"Failed to download file for zenodo.{zenodo_id}: {filename}"
                )

            # Checksum verification before writing to disk
            content_md5 = hashlib.md5(response.content).hexdigest()
            if content_md5 != checksum:
                raise InvalidChecksumError(
                    "Checksum mismatch: "
                    f"{filename} has invalid checksum ({content_md5})"
                )

            with output_dir.joinpath(filename).open("wb") as f:
                f.write(response.content)

    def _create_new_version(self, zenodo_id: str) -> str:
        response = httpx.post(
            f"{self.api_endpoint}/records/{zenodo_id}/versions",
            headers=self.headers,
        )
        if response.status_code != 201:
            raise ZenodoAPIError(
                f"Failed to create a new version for zenodo.{zenodo_id}:"
                + response.json()
            )

        # Zenodo Requires to update the metadata to include the publication date
        metadata = response.json()["metadata"]
        new_zenodo_id = response.json()["id"]

        creators = list()
        for creator in metadata["creators"]:
            family_name, given_name = creator["name"].split(", ")
            creators.append(
                {
                    "person_or_org": {
                        "given_name": given_name,
                        "family_name": family_name,
                        "type": "personal",
                    },
                }
            )

        updated_metadata = {
            "metadata": {
                "title": metadata["title"],
                "creators": creators,
                "publication_date": datetime.today().strftime("%Y-%m-%d"),
                "publisher": "Nipoppy",
                "resource_type": {"id": "dataset"},
            }
        }

        response = httpx.put(
            f"{self.api_endpoint}/records/{new_zenodo_id}/draft",
            headers=self.headers,
            json=updated_metadata,
        )
        if response.status_code != 200:
            raise ZenodoAPIError(
                f"Failed to update metadata for zenodo.{zenodo_id}:" + response.json()
            )

        return new_zenodo_id

    def _create_draft(self, metadata: dict) -> str:
        response = httpx.post(
            f"{self.api_endpoint}/records",
            headers=self.headers | {"Content-Type": "application/json"},
            json=metadata,
        )
        if response.status_code != 201:
            raise ZenodoAPIError(f"Failed to create a draft record: {response.json()}")

        return response.json()["id"]

    def _upload_files(self, files: list[Path], zenodo_id: str):
        try:
            metadata = [{"key": f.name for f in files}]
            response = httpx.post(
                f"{self.api_endpoint}/records/{zenodo_id}/draft/files",
                headers=self.headers | {"Content-Type": "application/json"},
                json=metadata,
            )
            if response.status_code != 201:
                raise ZenodoAPIError(
                    f"Failed to create upload file list for zenodo.{zenodo_id}: {files}"
                    + response.json()
                )
        except ZenodoAPIError as e:
            raise e

        for filename in files:
            # Upload the file content
            with filename.open("rb") as f:
                response = httpx.put(
                    f"{self.api_endpoint}/records/{zenodo_id}/draft/files/{filename.name}/content",  # noqa E501
                    headers=self.headers | {"Content-Type": "application/octet-stream"},
                    content=f,
                )
                if response.status_code != 200:
                    raise ZenodoAPIError(
                        f"Failed to upload file for zenodo.{zenodo_id}: {filename}"
                        + response.json()
                    )

            # Commit the uploaded file
            response = httpx.post(
                f"{self.api_endpoint}/records/{zenodo_id}/draft/files/{filename.name}/commit",  # noqa E501
                headers=self.headers,
            )
            if response.status_code != 200:
                raise ZenodoAPIError(
                    f"Failed to commit the file file for zenodo.{zenodo_id}: {filename}"
                    + response.json()
                )

    def _publish(self, zenodo_id: str) -> str:
        response = httpx.post(
            f"{self.api_endpoint}/records/{zenodo_id}/draft/actions/publish",
            headers=self.headers,
        )
        if response.status_code != 202:
            raise ZenodoAPIError(
                (f"Failed to publish zenodo.{zenodo_id}: {response.json()}")
            )

        return response.json()["links"]["self_doi"]

    def upload_pipeline(
        self, metadata: dict, files: list[Path], zenodo_id: Optional[str] = None
    ) -> Optional[str]:
        # TODO Add pipeline validation before uploading to Zenodo.

        if zenodo_id:
            zenodo_id = self._create_new_version(zenodo_id)
            action = "update"
        else:
            zenodo_id = self._create_draft(metadata)
            action = "creation"

        try:
            self._upload_files(files, zenodo_id)
            doi = self._publish(zenodo_id)
            return doi

        except Exception as e:
            # Delete the draft if an error occurs
            # Prevents issue when retrying to modify the record while a draft exits.
            print(f"Reverting record {action} for zenodo.{zenodo_id} due to error {e}")
            httpx.delete(
                f"{self.api_endpoint}/records/{zenodo_id}/draft",
                headers=self.headers,
            )
            print(f"Record {action} reverted")
            return None
