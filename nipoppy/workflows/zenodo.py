"""Workflow for interacting with Zenodo API."""

from typing import Optional

from nipoppy.env import StrOrPathLike
from nipoppy.workflows.base import BaseWorkflow

from pathlib import Path
from typing import Optional

import httpx

from nipoppy.utils import get_today, load_json
from nipoppy.env import LogColor, StrOrPathLike


import hashlib


class InvalidChecksumError(Exception):
    """Checksum mismatch between two files."""

    pass


class ZenodoAPIError(Exception):
    """Error when interacting with Zenodo API."""

    pass


class ZenodoWorkflow(BaseWorkflow):
    """Client to interact with Zenodo API.

    Zenodo uses the InvenioRDM API, which is documented at:
    https://inveniordm.docs.cern.ch/reference/rest_api_index/
    """

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        access_token: Optional[str] = None,
        sandbox: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose=False,
        dry_run=False,
        name: Optional[str] = None,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name=name,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

        self.sandbox = sandbox

        if self.sandbox:
            self.api_endpoint = "https://sandbox.zenodo.org/api"
        else:
            self.api_endpoint = "https://zenodo.org/api"

        # Access token is required for uploading files
        self.access_token = access_token
        if self.access_token is not None:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
            }
        else:
            self.headers = {}


class ZenodoUploadWorkflow(ZenodoWorkflow):
    """Workflow for Zenodo upload."""

    def __init__(
        self,
        dpath_pipeline: StrOrPathLike,
        zenodo_id: Optional[str] = None,
        access_token: Optional[str] = None,
        sandbox: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose=False,
        dry_run=False,
    ):
        self.dpath_pipeline = dpath_pipeline
        self.zenodo_id = zenodo_id

        dpath_root = Path(self.dpath_pipeline).parent.parent
        super().__init__(
            dpath_root=dpath_root,
            access_token=access_token,
            sandbox=sandbox,
            name="pipeline_upload",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

    def _create_new_version(self, zenodo_id: str, metadata: dict) -> str:
        response = httpx.post(
            f"{self.api_endpoint}/records/{zenodo_id}/versions",
            headers=self.headers,
        )
        if response.status_code != 201:
            raise ZenodoAPIError(
                f"Failed to create a new version for zenodo.{zenodo_id}:"
                + response.json()
            )
        new_zenodo_id = response.json()["id"]

        # Required to update the metadata to include the new publication date
        response = httpx.put(
            f"{self.api_endpoint}/records/{new_zenodo_id}/draft",
            headers=self.headers,
            json=metadata,
        )
        if response.status_code != 200:
            raise ZenodoAPIError(
                f"Failed to update metadata for zenodo.{zenodo_id}: {response.json()}"
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
        metadata = [{"key": file.name} for file in files]
        response = httpx.post(
            f"{self.api_endpoint}/records/{zenodo_id}/draft/files",
            headers=self.headers | {"Content-Type": "application/json"},
            json=metadata,
        )
        if response.status_code != 201:
            raise ZenodoAPIError(
                f"Failed to create upload file list for zenodo.{zenodo_id}: {files}"
                f"\n{response.json()}"
            )

        for file in files:
            # Upload the file content
            with file.open("rb") as f:
                response = httpx.put(
                    f"{self.api_endpoint}/records/{zenodo_id}/draft/files/{file.name}/content",  # noqa E501
                    headers=self.headers | {"Content-Type": "application/octet-stream"},
                    content=f,
                )
                if response.status_code != 200:
                    raise ZenodoAPIError(
                        f"Failed to upload file for zenodo.{zenodo_id}: {file.name}"
                        f"\n{response.json()}"
                    )

            # Commit the uploaded file
            response = httpx.post(
                f"{self.api_endpoint}/records/{zenodo_id}/draft/files/{file.name}/commit",  # noqa E501
                headers=self.headers,
            )
            if response.status_code != 200:
                raise ZenodoAPIError(
                    f"Failed to commit the file file for zenodo.{zenodo_id}: {file}"
                    f"\n{response.json()}"
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

    def _get_pipeline_metadata(
        self, zenodo_metadata: Path, pipeline_config: Path
    ) -> dict:
        # TODO Get metadata from the pipeline configuration file.
        metadata = {
            "metadata": {
                "publication_date": get_today(),
                "publisher": "Nipoppy",
                "resource_type": {"id": "software"},
                "keywords": [],
            }
        }

        pipeline_metadata = load_json(zenodo_metadata)
        metadata["metadata"].update(pipeline_metadata)

        # Enforce Nipoppy keywords
        config = load_json(pipeline_config)
        pipeline_type = config["PIPELINE_TYPE"]
        metadata["metadata"]["keywords"] = list(
            set(metadata["metadata"]["keywords"] + ["Nipoppy", pipeline_type])
        )

        return metadata

    def _check_authentication(self) -> None:
        response = httpx.get(
            f"{self.api_endpoint}/user/records",
            headers=self.headers | {"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            raise ZenodoAPIError(f"Failed to authenticate to Zenodo: {response.json()}")

    def upload_pipeline(
        self, input_dir: Path, zenodo_id: Optional[str] = None
    ) -> Optional[str]:
        """Upload a pipeline to Zenodo."""
        # TODO Add pipeline validation before uploading to Zenodo
        pipeline_config = ...

        if not input_dir.exists():
            raise FileNotFoundError(input_dir)
        if not input_dir.is_dir():
            raise ValueError(f"{input_dir} must be a directory.")

        self._check_authentication()

        zenodo_metadata = input_dir.joinpath("zenodo.json")  # Should use layout instead
        metadata = self._get_pipeline_metadata(zenodo_metadata, pipeline_config)
        if zenodo_id:
            zenodo_id = self._create_new_version(zenodo_id, metadata)
            action = "update"
        else:
            zenodo_id = self._create_draft(metadata)
            action = "creation"

        try:
            files = list(input_dir.iterdir())
            self._upload_files(files, zenodo_id)
            doi = self._publish(zenodo_id)
            return doi

        except Exception as e:
            # Delete the draft if an error occurs
            # Prevents issue when retrying to modify the record while a draft exits.
            self.logger.debug(
                f"Reverting record {action} for zenodo.{zenodo_id} due to error: {e}"
            )
            response = httpx.delete(
                f"{self.api_endpoint}/records/{zenodo_id}/draft",
                headers=self.headers,
            )
            if response == 204:
                self.logger.debug(f"Record {action} reverted")
            else:
                self.logger.debug(
                    f"Failed to revert record {action} for zenodo.{zenodo_id}"
                )

            return None

    def run_main(self):
        """Run the main workflow."""
        self.logger.info(f"Uploading pipeline from {self.dpath_pipeline}")
        self.upload_pipeline(input_dir=self.dpath_pipeline, zenodo_id=self.zenodo_id)
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully uploaded[/]",
        )


class ZenodoDownloadWorkflow(ZenodoWorkflow):
    """Workflow for Zenodo download."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        zenodo_id: Optional[str] = None,
        access_token: Optional[str] = None,
        force: bool = False,
        sandbox: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose=False,
        dry_run=False,
    ):
        self.zenodo_id = zenodo_id
        self.force = force

        super().__init__(
            dpath_root=dpath_root,
            access_token=access_token,
            sandbox=sandbox,
            name="pipeline_download",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

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
            raise ZenodoAPIError(
                f"Failed to get files for zenodo.{zenodo_id}: {response.json()}"
            )

        # Exclude "md5:" prefix
        files = {
            entry["key"]: entry["checksum"].removeprefix("md5:")
            for entry in response.json()["entries"]
        }
        for file, checksum in files.items():
            response = httpx.get(
                f"{self.api_endpoint}/records/{zenodo_id}/files/{file}/content",  # noqa E501
                headers=self.headers,
            )
            if response.status_code != 200:
                raise ZenodoAPIError(
                    f"Failed to download file for zenodo.{zenodo_id}: {file}"
                    f"\n{response.json()}"
                )

            # Checksum verification before writing to disk
            content_md5 = hashlib.md5(response.content).hexdigest()
            if content_md5 != checksum:
                raise InvalidChecksumError(
                    "Checksum mismatch: " f"'{file}' has invalid checksum {content_md5}"
                )

            output_dir.joinpath(file).write_bytes(response.content)

    def run_main(self):
        """Run the main workflow."""
        print(self.layout.config)
        return

        output_dir = self.layout.dpath_pipelines / self.zenodo_id
        if output_dir.exists() and not self.force:
            self.logger.error(
                f"Output directory {output_dir} already exists."
                "Use the '--force' flag to overwrite the current content. Aborting."
            )

        self.logger.info(f"Downloading pipeline {self.zenodo_id} in {output_dir}")
        self.download_record_files(zenodo_id=self.zenodo_id, output_dir=output_dir)
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully downloaded[/]",
        )

        pipeline_name = self.layout.config["NAME"]
        pipeline_version = self.layout.config["VERSION"]
        pipeline_dir = (
            self.layout.dpath_pipelines / f"{pipeline_name}-{pipeline_version}"
        )
        if pipeline_dir.exists() and not self.force:
            self.logger.error(
                f"Pipeline directory {pipeline_dir} already exists."
                "Use the '--force' flag to overwrite the current content. Aborting."
            )
        output_dir.rename(pipeline_dir)
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully moved to {pipeline_dir}[/]",
        )

        # TODO install the pipeline
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully installed[/]",
        )
