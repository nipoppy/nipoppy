"""Workflow for pipeline validate command."""

import json
from pathlib import Path
from typing import Optional

import boutiques as bosh

from nipoppy.env import TEMPLATE_PIPELINE_PATH, LogColor, PipelineTypeEnum
from nipoppy.workflows.base import BaseWorkflow


class PipelineCreateWorkflow(BaseWorkflow):
    """Workflow for pipeline validate command."""

    def __init__(
        self,
        target: Path,
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
        self.target = target
        self.type_ = type_
        self.source_descriptor = source_descriptor

    def run_main(self):
        """Run the main workflow."""
        self.logger.debug(f"Creating pipeline bundle at {self.target}")
        create_bundle(
            target=self.target,
            type_=self.type_,
            source_descriptor=self.source_descriptor,
        )
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline bundle successfully created at "
            f"{self.target}![/]",
        )
        self.logger.warning("Edit the files to customize your pipeline.")
        self.logger.info(
            "You can run [magenta]nipoppy validate[/] to check your pipeline"
            " configuration and [magenta]nipoppy upload[/] to upload it to Zenodo."
            "\nIt is recommended to test the pipeline with a small dataset before"
            " uploading it to Zenodo."
        )


def create_bundle(
    target: Path,
    type_: PipelineTypeEnum,
    *,
    source_descriptor: Optional[Path] = None,
):
    """Create a pipeline bundle."""
    if target.exists():
        raise IsADirectoryError(
            f"Target directory {target} already exists. "
            "Please remove it or choose a different name.",
        )
    else:
        target.mkdir(parents=True, exist_ok=True)

    descriptor_path = target / "descriptor.json"
    if source_descriptor:
        descriptor_path.write_text(source_descriptor.read_text())
    else:
        bosh.create(descriptor_path.as_posix())

    target.joinpath("invocation.json").write_text(
        bosh.example(descriptor_path.as_posix())
    )
    target.joinpath("hpc.json").write_text(
        TEMPLATE_PIPELINE_PATH.joinpath("hpc.json").read_text()
    )
    target.joinpath("zenodo.json").write_text(
        TEMPLATE_PIPELINE_PATH.joinpath("zenodo.json").read_text()
    )

    # Populate the config.json using descriptor information
    config = json.loads(
        TEMPLATE_PIPELINE_PATH.joinpath(f"config-{type_.value}.json").read_text()
    )
    descriptor = json.loads(descriptor_path.read_text())
    config["NAME"] = descriptor["name"]
    config["VERSION"] = descriptor["tool-version"]
    target.joinpath("config.json").write_text(json.dumps(config, indent=4))

    # Only PROCESSING pipelines have a tracker.json file
    if PipelineTypeEnum.PROCESSING:
        target.joinpath("tracker.json").write_text(
            TEMPLATE_PIPELINE_PATH.joinpath("tracker.json").read_text()
        )
