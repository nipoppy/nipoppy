"""Workflow for interacting with Zenodo API."""

import hashlib
from pathlib import Path

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.console import CONSOLE_STDOUT
from nipoppy.env import StrOrPathLike
from nipoppy.exceptions import TerminatedByUserError, WorkflowError
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

    def _is_same_record(self, record_id: str, input_dir: Path) -> bool:
        """Check whether local files match a published Zenodo record."""
        local_files = {
            file.name: _get_file_md5(file) for file in sorted(input_dir.iterdir())
        }
        remote_files = {
            entry["key"]: (
                entry["checksum"].lower()
                if ":" in entry["checksum"]
                else f"md5:{entry['checksum'].lower()}"
            )
            for entry in self.zenodo_api.get_record_files(record_id)["entries"]
        }
        return local_files == remote_files

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

        latest_record_id = None
        if self.record_id:
            self.record_id = self.record_id.removeprefix("zenodo.")
            latest_record_id = self.zenodo_api.get_latest_version_id(self.record_id)
            current_metadata = self.zenodo_api.get_record_metadata(latest_record_id)
            if not self.force and not _is_same_pipeline(
                pipeline_config, current_metadata
            ):
                raise WorkflowError(
                    "The pipeline metadata does not match the existing record "
                    f"(zenodo.{self.record_id}). Aborting."
                    "\nUse the --force flag to force the update."
                )
        else:
            pipeline_type = pipeline_config.PIPELINE_TYPE.value
            pipeline_name = pipeline_config.NAME
            pipeline_version = pipeline_config.VERSION
            records = self.zenodo_api.search_records(
                "",
                keywords=[
                    f"pipeline_type:{pipeline_type}",
                    f"pipeline_name:{pipeline_name}",
                    f"pipeline_version:{pipeline_version}",
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

        community_id = (
            self.zenodo_api.get_community_id("nipoppy") if self.community else None
        )

        if (
            latest_record_id is not None
            and not self.force
            and self._is_same_record(
                record_id=latest_record_id,
                input_dir=pipeline_dir,
            )
        ):
            logger.success(
                "Pipeline files are unchanged; skipping upload for "
                f"zenodo.{latest_record_id}."
            )
            if community_id is not None:
                self.zenodo_api.request_community_inclusion(
                    latest_record_id, community_id
                )
                logger.success("Nipoppy community inclusion request submitted.")
            return

        # Confirm upload
        if not self.assume_yes:
            continue_ = CONSOLE_STDOUT.confirm(
                "The Nipoppy pipeline will be uploaded/updated on Zenodo"
                f"{' (sandbox)' if self.zenodo_api.sandbox else ''},"
                " this is a [bold]permanent[/] action, are you sure?",
            )
            if not continue_:
                logger.warning("Zenodo upload cancelled.")
                raise TerminatedByUserError("User cancelled the upload.")

        zenodo_metadata = pipeline_dir.joinpath("zenodo.json")
        metadata = self._get_pipeline_metadata(zenodo_metadata, pipeline_config)

        doi = self.zenodo_api.upload_record(
            input_dir=pipeline_dir,
            record_id=self.record_id,
            metadata=metadata,
            default_preview_filename=DatasetLayout.fname_pipeline_config,
            community_id=community_id,
        )
        logger.success(f"Pipeline successfully uploaded at {doi}")
        if community_id is not None:
            logger.success("Nipoppy community inclusion request submitted.")

    def run_cleanup(self):
        """Close resources used by the workflow."""
        self.zenodo_api.close()


def _get_file_md5(file: Path) -> str:
    """Calculate the MD5 checksum used by Zenodo for uploaded files."""
    checksum = hashlib.md5(file.read_bytes())
    return f"md5:{checksum.hexdigest()}"


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
    pipeline_type = pipeline_config.PIPELINE_TYPE.value
    pipeline_name = pipeline_config.NAME
    pipeline_version = pipeline_config.VERSION

    return all(
        [
            keywords.count(f"pipeline_type:{pipeline_type}"),
            keywords.count(f"pipeline_name:{pipeline_name.lower()}"),
            keywords.count(f"pipeline_version:{pipeline_version}"),
        ]
    )
