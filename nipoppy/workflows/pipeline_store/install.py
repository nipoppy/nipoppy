"""Workflow for pipeline install command."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from nipoppy.config.main import Config
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.pipeline_store.validation import check_pipeline_bundle
from nipoppy.workflows.base import BaseDatasetWorkflow
from nipoppy.zenodo_api import ZenodoAPI


class PipelineInstallWorkflow(BaseDatasetWorkflow):
    """Workflow for pipeline install command."""

    def __init__(
        self,
        dpath_root: Path,
        dpath_pipeline_or_zenodo_id: StrOrPathLike | str,
        zenodo_api: ZenodoAPI = None,
        force: bool = False,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="pipeline_install",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logfile=True,
        )
        self.dpath_pipeline_or_zenodo_id = dpath_pipeline_or_zenodo_id
        self.zenodo_api = zenodo_api or ZenodoAPI()
        self.force = force

        self.zenodo_api.set_logger(self.logger)

        self.dpath_pipeline = None
        self.zenodo_id = None
        if (dpath_pipeline := Path(dpath_pipeline_or_zenodo_id)).exists():
            self.dpath_pipeline = dpath_pipeline.resolve()
        elif dpath_pipeline_or_zenodo_id.removeprefix("zenodo.").isnumeric():
            self.zenodo_id = dpath_pipeline_or_zenodo_id
        else:
            self.logger.warning(
                f"{dpath_pipeline_or_zenodo_id} does not seem like a valid path "
                "or Zenodo ID"
            )

    def _update_config_and_save(self, pipeline_config: BasePipelineConfig) -> Config:
        """
        Add pipeline variables (e.g. for user-defined paths) to the global config file.

        Notes
        -----
        This loads a new Config object (i.e., does not use already-loaded
        self.config object).
        """
        # do not use self.config since it has been changed by substitutions already
        config = self.config.load(self.layout.fpath_config, apply_substitutions=False)

        if len(pipeline_config.VARIABLES) == 0:
            self.logger.info("No changes to the global config file.")
            return config

        # update config
        config.PIPELINE_VARIABLES.set_variables(
            pipeline_config.PIPELINE_TYPE,
            pipeline_config.NAME,
            pipeline_config.VERSION,
            {variable_name: None for variable_name in pipeline_config.VARIABLES},
        )

        # log variable details
        self.logger.info(
            f"Adding {len(pipeline_config.VARIABLES)} variable(s) "
            "to the global config file:"
        )
        for (
            variable_name,
            variable_description,
        ) in pipeline_config.VARIABLES.items():
            self.logger.info(f"\t{variable_name}\t{variable_description}")
        self.logger.warning(
            "You must update the PIPELINE_VARIABLES section in "
            f"{self.layout.fpath_config} manually before running the pipeline!"
        )

        # save
        if not self.dry_run:
            config.save(self.layout.fpath_config)

        return config

    def run_main(self):
        """Install a pipeline.

        The pipeline config directory is put in the appropriate location in the dataset,
        and any pipeline variables are added to the global config file.
        """
        if self.zenodo_id is not None:
            dpath_pipeline = self.layout.dpath_pipelines / self.zenodo_id
            if dpath_pipeline.exists() and not self.force:
                self.logger.error(
                    f"Output directory {dpath_pipeline} already exists."
                    "Use the '--force' flag to overwrite the current content. Aborting."
                )
                raise SystemExit(1)

            self.logger.info(
                f"Downloading pipeline {self.zenodo_id} in {dpath_pipeline}"
            )
            self.zenodo_api.download_record_files(
                record_id=self.zenodo_id, output_dir=dpath_pipeline
            )
            self.logger.info(
                f"[{LogColor.SUCCESS}]Pipeline successfully downloaded[/]",
            )
        else:
            dpath_pipeline = self.dpath_pipeline

        # load the config and validate file contents (including file paths)
        pipeline_config = check_pipeline_bundle(
            dpath_pipeline,
            logger=self.logger,
        )

        # generate destination path
        dpath_target = self.layout.get_dpath_pipeline_bundle(
            pipeline_config.PIPELINE_TYPE, pipeline_config.NAME, pipeline_config.VERSION
        )

        # check if the target directory already exists
        if dpath_target.exists():
            if not self.force:
                raise FileExistsError(
                    f"Pipeline directory exists: {dpath_target}"
                    ". Use --force to overwrite",
                )
            else:
                self.rm(dpath_target, log_level=logging.DEBUG)

        # copy the directory
        if self.dpath_pipeline is not None:
            self.copytree(
                path_source=dpath_pipeline,
                path_dest=dpath_target,
                log_level=logging.DEBUG,
            )
        else:
            # if the pipeline was downloaded from Zenodo, move it to the target location
            self.movetree(
                path_source=dpath_pipeline,
                path_dest=dpath_target,
                log_level=logging.DEBUG,
            )
            self.rm(dpath_pipeline, log_level=logging.DEBUG)

        # update global config with new pipeline variables
        self._update_config_and_save(pipeline_config)

        self.logger.info(
            f"[{LogColor.SUCCESS}]Successfully installed pipeline "
            f"{pipeline_config.NAME}, version {pipeline_config.VERSION} "
            f"at {dpath_target}![/]"
        )
