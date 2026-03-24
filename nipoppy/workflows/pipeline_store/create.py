"""Workflow for pipeline validate command."""

from pathlib import Path
from typing import Optional

import boutiques

from nipoppy.env import PipelineTypeEnum
from nipoppy.exceptions import FileOperationError, WorkflowError
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.utils import fileops
from nipoppy.utils.utils import TEMPLATE_PIPELINE_PATH, load_json, save_json
from nipoppy.workflows.base import BaseWorkflow

logger = get_logger()


class PipelineCreateWorkflow(BaseWorkflow):
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
            try:
                boutiques.validate(str(source_descriptor))
            except boutiques.DescriptorValidationError as exception:
                raise WorkflowError(
                    f"Descriptor file {source_descriptor} is invalid:\n{exception}"
                )
            except ValueError as exception:  # catches simplejson.errors.JSONDecodeError
                raise WorkflowError(
                    "Error validating the descriptor file "
                    f"{source_descriptor}:\n{exception}"
                )
            fileops.copy(source_descriptor, descriptor_path, dry_run=self.dry_run)
        else:
            boutiques.create(str(descriptor_path))

        target.joinpath("invocation.json").write_text(
            boutiques.example(str(descriptor_path))
        )
        fileops.copy(
            TEMPLATE_PIPELINE_PATH.joinpath("hpc.json"),
            target.joinpath("hpc.json"),
            dry_run=self.dry_run,
        )

        config = load_json(
            TEMPLATE_PIPELINE_PATH.joinpath(f"config-{type_.value}.json")
        )

        # Populate the config.json using descriptor information
        if source_descriptor is not None:

            descriptor = load_json(descriptor_path)
            config["NAME"] = descriptor["name"]
            config["VERSION"] = descriptor["tool-version"]
            if "container-image" in descriptor:
                config["CONTAINER_INFO"][
                    "URI"
                ] = f"docker://{descriptor['container-image']['image']}"

                # replace the pipeline name/version with placeholders
                # to avoid users forgetting to update them when copy-pasting
                config["CONTAINER_INFO"]["URI"] = config["CONTAINER_INFO"][
                    "URI"
                ].replace(descriptor["name"], "[[PIPELINE_NAME]]")
                config["CONTAINER_INFO"]["URI"] = config["CONTAINER_INFO"][
                    "URI"
                ].replace(descriptor["tool-version"], "[[PIPELINE_VERSION]]")

        save_json(config, target.joinpath(DatasetLayout.fname_pipeline_config))

        # Only PROCESSING pipelines have a tracker.json file
        if self.type_ == PipelineTypeEnum.PROCESSING:
            fileops.copy(
                TEMPLATE_PIPELINE_PATH.joinpath("tracker.json"),
                target.joinpath("tracker.json"),
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
