"""Workflow for interacting with Zenodo API."""

import hashlib
from pathlib import Path

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.console import CONSOLE_STDOUT
from nipoppy.env import StrOrPathLike
from nipoppy.exceptions import ExecutionError, TerminatedByUserError, WorkflowError
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.utils.utils import get_today, load_json
from nipoppy.workflows.base import BaseWorkflow
from nipoppy.zenodo_api import ZenodoAPI

logger = get_logger()


class PipelineUploadWorkflow(BaseWorkflow):
    """Workflow for Zenodo upload."""

    def __init__(
        self,
        dpath_pipeline: StrOrPathLike,
        zenodo_api: ZenodoAPI | None = None,
        record_id: str | None = None,
        assume_yes: bool = False,
        force: bool = False,
        community: bool = False,
        verbose=False,
        dry_run=False,
    ):
        self.dpath_pipeline = dpath_pipeline
        self.zenodo_api = zenodo_api or ZenodoAPI()
        self.zenodo_api.logger = logger  # use nipoppy logger configuration
        self.record_id = record_id
        self.assume_yes = assume_yes
        self.force = force
        self.community = community

        super().__init__(
            name="pipeline_upload",
            verbose=verbose,
            dry_run=dry_run,
        )

    def _get_pipeline_metadata(
        self, zenodo_metadata_file: Path, pipeline_config: BasePipelineConfig
    ) -> dict:
        default_description = (
            "Nipoppy configuration files for "
            f"{pipeline_config.NAME} {pipeline_config.VERSION} pipeline"
        )
        metadata = {
            "metadata": {
                "title": f"{pipeline_config.NAME}-{pipeline_config.VERSION}",
                "description": (pipeline_config.DESCRIPTION or default_description),
                "publication_date": get_today(),
                "publisher": "Nipoppy",
                "creators": [],  # to be set by user or ZenodoAPI
                "resource_type": {"id": "software"},
                "subjects": [],
            }
        }

        if zenodo_metadata_file.exists():
            logger.info(f"Loading metadata from {zenodo_metadata_file}")
            pipeline_metadata = load_json(zenodo_metadata_file)
            metadata["metadata"].update(pipeline_metadata)

        # Enforce Nipoppy keywords
        for keyword in [
            "Nipoppy",
            f"pipeline_type:{pipeline_config.PIPELINE_TYPE.value}",
            f"pipeline_name:{pipeline_config.NAME.lower()}",
            f"pipeline_version:{pipeline_config.VERSION}",
            f"schema_version:{pipeline_config.SCHEMA_VERSION}",
        ]:
            if (keyword_dict := {"subject": keyword}) not in metadata["metadata"][
                "subjects"
            ]:
                metadata["metadata"]["subjects"].append(keyword_dict)

        return metadata

    def _is_same_record(self, record_id: str | None, input_dir: Path) -> bool:
        """Check whether local files match a published Zenodo record."""
        if record_id is None:
            return False

        local_files = {
            file.name: _get_file_md5(file) for file in sorted(input_dir.iterdir())
        }
        remote_files = self.zenodo_api.get_record_files(record_id)
        return local_files == remote_files

    def _confirm_upload(self) -> None:
        """Confirm upload with the user."""
        if self.assume_yes:
            logger.debug("Assuming yes to all prompts (--assume-yes flag).")
            return

        if not CONSOLE_STDOUT.is_interactive or not CONSOLE_STDOUT.is_terminal:
            raise ExecutionError(
                "Non-interactive terminal detected."
                " Use the --assume-yes flag to bypass this prompt."
            )

        if not CONSOLE_STDOUT.confirm(
            "The Nipoppy pipeline will be uploaded/updated on Zenodo"
            f"{' (sandbox)' if self.zenodo_api.sandbox else ''},"
            " this is a [bold]permanent[/] action, are you sure?",
        ):
            raise TerminatedByUserError("Zenodo upload cancelled by user.")

    def _request_community_inclusion(self, record_id: str):
        if self.community:
            self.zenodo_api.request_community_inclusion(
                record_id=record_id,
                community_id=self.zenodo_api.get_community_id("nipoppy"),
            )
        else:
            logger.info(
                "Use the --community flag to request inclusion in the Nipoppy Zenodo "
                "community."
            )

    def run_main(self):
        """Run the main workflow."""
        pipeline_dir = Path(self.dpath_pipeline)
        logger.info(f"Uploading pipeline from {pipeline_dir}")

        # Safeguard before uploading
        try:
            pipeline_config = check_pipeline_bundle(pipeline_dir, strict=True)
        except Exception as e:
            logger.error(
                f"Pipeline validation failed. Please check the pipeline files: {e}"
            )
            raise WorkflowError from e

        if self.record_id:
            # If a record ID is provided, get it's latest Zenodo version and metadata
            self.record_id = self.zenodo_api.get_latest_version_id(self.record_id)
            record_metadata = self.zenodo_api.get_record_metadata(self.record_id)

            if not self.force and not _is_same_pipeline(
                pipeline_config, record_metadata
            ):
                raise WorkflowError(
                    "The pipeline metadata does not match the existing record "
                    f"({self.record_id}). Aborting."
                    "\nUse the --force flag to force the update."
                )
        else:
            records = self.zenodo_api.search_records(
                "",
                keywords=[
                    f"pipeline_type:{pipeline_config.PIPELINE_TYPE.value}",
                    f"pipeline_name:{pipeline_config.NAME}",
                    f"pipeline_version:{pipeline_config.VERSION}",
                ],
            )["hits"]

            if not self.force and len(records) > 0:
                potential_duplicates = [
                    record["links"]["self_html"] for record in records
                ]
                raise WorkflowError(
                    "It looks like this pipeline already exists in Zenodo. Aborting."
                    "\nPlease use the --zenodo-id flag to update it or the"
                    " --force flag to force the upload."
                    f"\nFound {len(records)} potential duplicates: "
                    f"{', '.join(potential_duplicates)}",
                )

        if not self.force and self._is_same_record(
            record_id=self.record_id,
            input_dir=pipeline_dir,
        ):
            logger.warning(
                f"Pipeline files are unchanged; skipping upload for {self.record_id}."
            )
        else:
            self._confirm_upload()

            metadata = self._get_pipeline_metadata(
                zenodo_metadata_file=pipeline_dir.joinpath("zenodo.json"),
                pipeline_config=pipeline_config,
            )

            doi = self.zenodo_api.upload_record(
                input_dir=pipeline_dir,
                record_id=self.record_id,
                metadata=metadata,
                default_preview_filename=DatasetLayout.fname_pipeline_config,
            )
            logger.success(f"Pipeline successfully uploaded at {doi}")
            self.record_id = doi.split("/")[-1]  # extract record ID from DOI URL

        self._request_community_inclusion(self.record_id)

    def run_cleanup(self):
        """Close resources used by the workflow."""
        self.zenodo_api.close()


def _get_file_md5(file: Path) -> str:
    """Calculate the MD5 checksum used by Zenodo for uploaded files."""
    checksum = hashlib.md5(file.read_bytes())
    return checksum.hexdigest()


def _is_same_pipeline(
    pipeline_config: BasePipelineConfig, zenodo_metadata: dict
) -> bool:
    """Check if two pipelines are the same.

    This is done by comparing the pipeline
        - type
        - name
        - version

    Parameters
    ----------
    pipeline_config : BasePipelineConfig
        Pipeline configuration.
    zenodo_metadata : dict
        Zenodo metadata.

    Returns
    -------
    bool
        True if the pipelines are the same, False otherwise.
    """
    keywords = zenodo_metadata.get("keywords", [])
    return all(
        [
            keywords.count(f"pipeline_type:{pipeline_config.PIPELINE_TYPE.value}"),
            keywords.count(f"pipeline_name:{pipeline_config.NAME.lower()}"),
            keywords.count(f"pipeline_version:{pipeline_config.VERSION}"),
        ]
    )
