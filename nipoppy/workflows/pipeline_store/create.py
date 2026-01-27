"""Workflow for pipeline validate command."""

from pathlib import Path
from typing import Optional

import boutiques as bosh

from nipoppy.env import PipelineTypeEnum
from nipoppy.exceptions import FileOperationError
from nipoppy.logger import get_logger
from nipoppy.utils import fileops
from nipoppy.utils.utils import TEMPLATE_PIPELINE_PATH, load_json, save_json
from nipoppy.workflows.base import Workflow

logger = get_logger()


class PipelineCreateWorkflow(Workflow):
    """Workflow for pipeline validate command."""

    def __init__(
        self,
        pipeline_dir: Path,
        type_: PipelineTypeEnum,
        *,
        source_descriptor: Optional[Path] = None,
        verbose=False,
        dry_run=False,
    ):
        super().__init__(
            name="pipeline_create",
            verbose=verbose,
            dry_run=dry_run,
        )
        self.pipeline_dir = pipeline_dir
        self.type_ = type_
        self.source_descriptor = source_descriptor

    def create_bundle(
        self,
        target: Path,
        type_: PipelineTypeEnum,
        *,
        source_descriptor: Optional[Path] = None,
    ):
        """Create a pipeline bundle."""
        if target.exists():
            raise FileOperationError(
                f"Target directory {target} already exists. "
                "Please remove it or choose a different name.",
            )
        else:
            target.mkdir(parents=True, exist_ok=True)

        descriptor_path = target / "descriptor.json"
        if source_descriptor:
            fileops.copy(source_descriptor, descriptor_path, dry_run=self.dry_run)
        else:
            bosh.create(descriptor_path.as_posix())

        target.joinpath("invocation.json").write_text(
            bosh.example(descriptor_path.as_posix())
        )
        fileops.copy(
            TEMPLATE_PIPELINE_PATH.joinpath("hpc.json"),
            target.joinpath("hpc.json"),
            dry_run=self.dry_run,
        )

        # Populate the config.json using descriptor information
        config = load_json(
            TEMPLATE_PIPELINE_PATH.joinpath(f"config-{type_.value}.json")
        )
        descriptor = load_json(descriptor_path)
        config["NAME"] = descriptor["name"]
        config["VERSION"] = descriptor["tool-version"]
        save_json(config, target.joinpath("config.json"))

        # Only PROCESSING pipelines have a tracker.json file
        if self.type_ == PipelineTypeEnum.PROCESSING:
            fileops.copy(
                TEMPLATE_PIPELINE_PATH.joinpath("tracker.json"),
                target.joinpath("tracker.json"),
                dry_run=self.dry_run,
            )
            fileops.copy(
                TEMPLATE_PIPELINE_PATH.joinpath("pybids_ignore.json"),
                target.joinpath("pybids_ignore.json"),
                dry_run=self.dry_run,
            )

    def run_main(self):
        """Run the main workflow."""
        logger.debug(f"Creating pipeline bundle at {self.pipeline_dir}")
        self.create_bundle(
            target=self.pipeline_dir,
            type_=self.type_,
            source_descriptor=self.source_descriptor,
        )
        logger.success(f"Pipeline bundle successfully created at {self.pipeline_dir}!")
        logger.warning("Edit the files to customize your pipeline.")
        logger.info(
            "You can run [magenta]nipoppy pipeline validate[/] to check your pipeline"
            " configuration and [magenta]nipoppy pipeline upload[/] to upload it to "
            "Zenodo."
            "\nIt is recommended to test the pipeline with a small dataset "
            "before uploading it to Zenodo."
        )
