"""Workflow for interacting with Zenodo API."""

from pathlib import Path
from typing import Optional

from rich.prompt import Confirm

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.pipeline_store.validation import check_pipeline_bundle
from nipoppy.utils import get_today, load_json
from nipoppy.workflows.base import BaseWorkflow
from nipoppy.zenodo_api import ZenodoAPI


class ZenodoUploadWorkflow(BaseWorkflow):
    """Workflow for Zenodo upload."""

    def __init__(
        self,
        dpath_pipeline: StrOrPathLike,
        zenodo_api: ZenodoAPI,
        record_id: Optional[str] = None,
        verbose=False,
        dry_run=False,
    ):
        self.dpath_pipeline = dpath_pipeline
        self.zenodo_api = zenodo_api
        self.record_id = record_id

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
        continue_ = Confirm.ask(
            "The Nipoppy pipeline will be uploaded/updated on Zenodo,"
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

        zenodo_metadata = pipeline_dir.joinpath("zenodo.json")
        metadata = self._get_pipeline_metadata(zenodo_metadata, pipeline_config)
        doi = self.zenodo_api.upload_pipeline(
            input_dir=pipeline_dir, record_id=self.record_id, metadata=metadata
        )
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully uploaded at {doi}[/]",
        )
