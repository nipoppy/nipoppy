"""Workflow for interacting with Zenodo API."""

import shutil
from pathlib import Path
from typing import Optional

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.pipeline_store.validation import check_pipeline_bundle
from nipoppy.utils import get_today, load_json
from nipoppy.workflows.base import BaseDatasetWorkflow, BaseWorkflow
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

    def get_creators(self):
        """Get the list of creators for the Zenodo metadata."""
        # TODO fetch user information from zenodo
        return [
            {
                "person_or_org": {
                    "family_name": "Nipoppy user",
                    "type": "personal",
                }
            }
        ]

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
                "creators": self.get_creators(),
                "resource_type": {"id": "software"},
                "subjects": [],
            }
        }

        if zenodo_metadata_file.exists():
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


class ZenodoDownloadWorkflow(BaseDatasetWorkflow):
    """Workflow for Zenodo download."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        record_id: str,
        zenodo_api: ZenodoAPI,
        force: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose=False,
        dry_run=False,
    ):
        self.record_id = record_id
        self.zenodo_api = zenodo_api
        self.force = force

        super().__init__(
            dpath_root=dpath_root,
            name="pipeline_download",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )

    def run_main(self):
        """Run the main workflow."""
        output_dir = self.layout.dpath_pipelines / self.record_id
        if output_dir.exists() and not self.force:
            self.logger.error(
                f"Output directory {output_dir} already exists."
                "Use the '--force' flag to overwrite the current content. Aborting."
            )
            raise SystemExit(1)

        self.logger.info(f"Downloading pipeline {self.record_id} in {output_dir}")
        self.zenodo_api.download_record_files(
            record_id=self.record_id, output_dir=output_dir
        )
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully downloaded[/]",
        )

        pipeline_config = load_json(output_dir / "config.json")
        pipeline_dir = (
            self.layout.dpath_pipelines
            / f"{pipeline_config['NAME']}-{pipeline_config['VERSION']}"
        )
        if pipeline_dir.exists():
            if self.force:
                self.logger.warning(
                    f"Pipeline directory {pipeline_dir} already exists."
                    " Overwriting the current content."
                )
                shutil.rmtree(pipeline_dir)
            else:
                self.logger.error(
                    f"Pipeline directory {pipeline_dir} already exists."
                    "Use the '--force' flag to overwrite the current content. Aborting."
                )
                raise SystemExit(1)

        output_dir.rename(pipeline_dir)
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully moved to {pipeline_dir}[/]",
        )

        # TODO install the pipeline
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline successfully installed[/]",
        )
