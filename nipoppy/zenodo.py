"""Client for Zenodo API."""

import hashlib
from pathlib import Path

import httpx


class InvalidChecksumError(Exception):
    """Checksum mismatch between two files."""

    pass


class ZenodoAPI:
    """Client to interact with Zenodo API.

    Zenodo uses the InvenioRDM API, which is documented at:
    https://inveniordm.docs.cern.ch/reference/rest_api_index/
    """

    def __init__(self, api_endpoint: str, access_token: str):
        self.api_endpoint = api_endpoint
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

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
        output_dir.mkdir(parents=True, exist_ok=True)
        response = httpx.get(
            f"{self.api_endpoint}/records/{zenodo_id}/files",
            headers=self.headers,
        )
        if response.status_code != 200:
            raise Exception(response.json())

        # Exclude "md5:" prefix
        files = {
            entry["key"]: entry["checksum"].removeprefix("md5:") for entry in response.json()["entries"]
        }
        for filename, checksum in files.items():
            response = httpx.get(
                f"{self.api_endpoint}/records/{zenodo_id}/files/{filename}/content",  # noqa E501
                headers=self.headers,
            )
            if response.status_code != 200:
                raise Exception(response.json())

            # Checksum verification before writing to disk
            content_md5 = hashlib.md5(response.content).hexdigest()
            if content_md5 != checksum:
                raise InvalidChecksumError(f"Checksum mismatch: {filename}")

            with output_dir.joinpath(filename).open("wb") as f:
                f.write(response.content)
