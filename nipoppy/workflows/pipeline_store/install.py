"""Workflow for pipeline install command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from nipoppy.config.main import Config
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.console import CONSOLE_STDERR, CONSOLE_STDOUT
from nipoppy.container import get_container_handler
from nipoppy.env import ContainerCommandEnum, StrOrPathLike
from nipoppy.exceptions import (
    ConfigError,
    FileOperationError,
    WorkflowError,
)
from nipoppy.logger import get_logger
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.utils import fileops
from nipoppy.utils.utils import apply_substitutions_to_json, process_template_str
from nipoppy.workflows.base import BaseDatasetWorkflow, _run_command
from nipoppy.zenodo_api import ZenodoAPI

logger = get_logger()


class PipelineInstallWorkflow(BaseDatasetWorkflow):
    """Workflow for pipeline install command."""

    def __init__(
        self,
        dpath_root: Path,
        source: StrOrPathLike | str,
        zenodo_api: ZenodoAPI = None,
        assume_yes: bool = False,
        force: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="nipoppy_pipeline_install",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
        )
        self.source = source
        self.zenodo_api = zenodo_api or ZenodoAPI()
        self.zenodo_api.logger = logger  # use nipoppy logger configuration
        self.assume_yes = assume_yes
        self.force = force

        self.dpath_pipeline = None
        self.zenodo_id = None
        if (dpath_pipeline := Path(source)).exists():
            self.dpath_pipeline = dpath_pipeline.resolve()
        elif source.removeprefix("zenodo.").isnumeric():
            self.zenodo_id = source
        else:
            logger.warning(f"{source} does not seem like a valid path or Zenodo ID")

    def _update_config_and_save(self, pipeline_config: BasePipelineConfig) -> Config:
        """
        Add pipeline variables (e.g. for user-defined paths) to the global config file.

        Notes
        -----
        This loads a new Config object (i.e., does not use already-loaded
        self.study.config object).
        """
        # do not use self.study.config since
        # it has been changed by substitutions already
        config = self.study.config.load(
            self.study.layout.fpath_config, apply_substitutions=False
        )

        if len(pipeline_config.VARIABLES) == 0:
            logger.debug("No changes to the global config file.")
            return config

        # update config
        # set variables value to None unless if they have not already been set
        variables = {variable_name: None for variable_name in pipeline_config.VARIABLES}
        variables.update(
            config.PIPELINE_VARIABLES.get_variables(
                pipeline_config.PIPELINE_TYPE,
                pipeline_config.NAME,
                pipeline_config.VERSION,
            )
        )
        config.PIPELINE_VARIABLES.set_variables(
            pipeline_config.PIPELINE_TYPE,
            pipeline_config.NAME,
            pipeline_config.VERSION,
            variables,
        )

        added_variables = [
            variable_name
            for variable_name, variable_value in variables.items()
            if variable_value is None
        ]

        if len(added_variables) > 0:
            # log variable details
            logger.warning(
                f"Adding {len(added_variables)} variable(s) to the global config file:"
            )
            for variable_name in added_variables:
                variable_description = pipeline_config.VARIABLES[variable_name]
                logger.warning(f"\t{variable_name}\t{variable_description}")
            logger.warning(
                "You must update the PIPELINE_VARIABLES section in "
                f"{self.study.layout.fpath_config}"
                " manually before running the pipeline!"
            )

            # save
            if not self.dry_run:
                config.save(self.study.layout.fpath_config)

        return config

    def _download_container(self, pipeline_config: BasePipelineConfig):
        uri = pipeline_config.CONTAINER_INFO.URI

        # pipeline is not containerized
        if uri is None:
            return

        # apply substitutions
        pipeline_config = type(pipeline_config)(
            **apply_substitutions_to_json(
                pipeline_config.model_dump(mode="json"), self.study.config.SUBSTITUTIONS
            )
        )
        fpath_container = Path(
            process_template_str(
                str(pipeline_config.CONTAINER_INFO.FILE), objs=[self.study.layout]
            )
        )

        container_handler = get_container_handler(self.study.config.CONTAINER_CONFIG)

        # container file already exists
        if container_handler.is_image_downloaded(uri, fpath_container):
            return

        # prompt user and confirm
        if self.assume_yes or CONSOLE_STDOUT.confirm(
            (
                f"[yellow]{container_handler.get_pull_confirmation_prompt(fpath_container)}[/]"  # noqa: E501
            ),
            kwargs_call={"default": True},
        ):
            pull_command = container_handler.get_pull_command(uri, fpath_container)

            if (
                self.study.config.CONTAINER_CONFIG.COMMAND
                == ContainerCommandEnum.DOCKER
            ):
                console = CONSOLE_STDOUT
            else:
                # use stderr for status messages so that the Apptainer/Singularity
                # output does not break the status display
                # ("apptainer/singularity pull" seems to only print to stderr)
                console = CONSOLE_STDERR

            try:
                with console.status(
                    "Downloading the container, this can take a while..."
                ):
                    _run_command(pull_command, dry_run=self.dry_run)
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to download container {pipeline_config.CONTAINER_INFO.URI}"
                    f": {e}"
                )
                raise WorkflowError from e

    def run_main(self):
        """Install a pipeline.

        The pipeline config directory is put in the appropriate location in the dataset,
        and any pipeline variables are added to the global config file.
        """
        if self.zenodo_id is not None:
            # TODO extract the function to the zenodo_api module
            record_source = (
                self.zenodo_api.api_endpoint.removesuffix("api")
                + "records/"
                + self.zenodo_id
            )
            logger.info(f"Installing pipeline from {record_source}")
            dpath_pipeline = self.study.layout.dpath_pipelines / self.zenodo_id
            if dpath_pipeline.exists() and not self.force:
                logger.error(
                    f"Output directory {dpath_pipeline} already exists."
                    "Use the '--force' flag to overwrite the current content. Aborting."
                )
                raise WorkflowError

            logger.debug(f"Downloading pipeline {self.zenodo_id} in {dpath_pipeline}")
            self.zenodo_api.download_record_files(
                record_id=self.zenodo_id, output_dir=dpath_pipeline
            )
            logger.success("Pipeline successfully downloaded")
        else:
            logger.info(f"Installing pipeline from {self.source}")
            dpath_pipeline = self.dpath_pipeline

        # load the config and validate file contents (including file paths)
        try:
            pipeline_config = check_pipeline_bundle(dpath_pipeline)
        except FileOperationError as e:
            # if the files were downloaded from Zenodo, point user to the Zenodo record
            if self.zenodo_id is not None:
                record_url = (
                    self.zenodo_api.api_endpoint.removesuffix("/api")
                    + "/records/"
                    + self.zenodo_id
                )
                raise ConfigError(
                    f"{str(e)}. Make sure the record at "
                    f"{record_url} contains valid Nipoppy pipeline configuration files."
                ) from e
            else:
                raise

        # generate destination path
        dpath_target = self.study.layout.get_dpath_pipeline_bundle(
            pipeline_config.PIPELINE_TYPE, pipeline_config.NAME, pipeline_config.VERSION
        )

        # check if the target directory already exists
        if dpath_target.exists():
            if not self.force:
                raise FileOperationError(
                    f"Pipeline directory exists: {dpath_target}"
                    ". Use --force to overwrite",
                )
            else:
                fileops.rm(dpath_target, dry_run=self.dry_run)

        # copy the directory
        if self.dpath_pipeline is not None:
            fileops.copy(
                source=dpath_pipeline,
                target=dpath_target,
                dry_run=self.dry_run,
            )
        else:
            # if the pipeline was downloaded from Zenodo, move it to the target location
            fileops.movetree(
                source=dpath_pipeline,
                target=dpath_target,
                dry_run=self.dry_run,
            )

        # update global config with new pipeline variables
        self._update_config_and_save(pipeline_config)

        # download container if it is specified
        self._download_container(pipeline_config)

        logger.success(
            "Successfully installed pipeline "
            f"{pipeline_config.NAME}, version {pipeline_config.VERSION} at "
            f"{dpath_target}"
        )
