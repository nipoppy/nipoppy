"""Workflow for interacting with Zenodo API."""

from pathlib import Path
from typing import Optional

from rich.prompt import Confirm

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.utils import get_today, load_json
from nipoppy.workflows.base import BaseWorkflow
from nipoppy.zenodo_api import ZenodoAPI, ZenodoAPIError


class ZenodoUploadWorkflow(BaseWorkflow):
    """Workflow for Zenodo upload."""

    def __init__(
        self,
        dpath_pipeline: StrOrPathLike,
        zenodo_api: ZenodoAPI,
        record_id: Optional[str] = None,
        assume_yes: bool = False,
        force: bool = False,
        verbose=False,
        dry_run=False,
    ):
        self.dpath_pipeline = dpath_pipeline
        self.zenodo_api = zenodo_api
        self.record_id = record_id
        self.assume_yes = assume_yes
        self.force = force

        super().__init__(
            name="pipeline_upload",
            verbose=verbose,
            dry_run=dry_run,
        )

        self.zenodo_api.set_logger(self.logger)

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
            self.logger.info(f"Loading metadata from {zenodo_metadata_file}")
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

    def run_main(self):
        """Run the main workflow."""
        if not self.assume_yes:
            continue_ = Confirm.ask(
                "The Nipoppy pipeline will be uploaded/updated on Zenodo"
                f"{' (sanbox) 'if self.zenodo_api.sandbox else ''},"
                " this is a [bold]permanent[/] action."
            )
            if not continue_:
                self.logger.info("Zenodo upload cancelled.")
                raise SystemExit(1)

        pipeline_dir = Path(self.dpath_pipeline)
        self.logger.info(f"Uploading pipeline from {pipeline_dir}")

        try:
            pipeline_config = check_pipeline_bundle(pipeline_dir, logger=self.logger)
        except Exception as e:
            self.logger.error(
                f"Pipeline validation failed. Please check the pipeline files: {e}"
            )
            raise SystemExit(1)

        if self.record_id:
            self.record_id = self.record_id.removeprefix("zenodo.")
            current_metadata = self.zenodo_api.get_record_metadata(self.record_id)
            if not self.force and not _is_same_pipeline(
                pipeline_config, current_metadata
            ):
                raise ZenodoAPIError(
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
                raise ZenodoAPIError(
                    "It looks like this pipeline already exist in Zenodo. Aborting."
                    "\nPlease use the --record-id flag to update it or the"
                    " --force flag to force the upload."
                )

        zenodo_metadata = pipeline_dir.joinpath("zenodo.json")
        metadata = self._get_pipeline_metadata(zenodo_metadata, pipeline_config)
        doi = self.zenodo_api.upload_pipeline(
            input_dir=pipeline_dir, record_id=self.record_id, metadata=metadata
        )
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully uploaded at {doi}[/]",
        )


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
    keywords = zenodo_metadata["keywords"]
    pipeline_type = pipeline_config.PIPELINE_TYPE.value
    pipeline_name = pipeline_config.NAME
    pipeline_version = pipeline_config.VERSION

    return all(
        [
            keywords.count(f"pipeline_type:{pipeline_type}"),
            keywords.count(f"pipeline_name:{pipeline_name}"),
            keywords.count(f"pipeline_version:{pipeline_version}"),
        ]
    )
