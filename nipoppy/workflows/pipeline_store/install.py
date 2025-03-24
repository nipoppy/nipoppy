"""Workflow for pipeline install command."""

import logging
from pathlib import Path
from typing import Optional

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import LogColor, StrOrPathLike
from nipoppy.pipeline_store.validation import check_pipeline_bundle
from nipoppy.workflows.base import BaseWorkflow


class PipelineInstallWorkflow(BaseWorkflow):
    """Workflow for pipeline install command."""

    def __init__(
        self,
        dpath_root: Path,
        dpath_pipeline: StrOrPathLike,
        overwrite: bool = False,
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
            _skip_logging=True,
        )
        self.dpath_pipeline = dpath_pipeline
        self.overwrite = overwrite

    def _add_variables_to_config(self, pipeline_config: BasePipelineConfig):
        if len(pipeline_config.VARIABLES) == 0:
            return

        # update config
        self.config.PIPELINE_VARIABLES.set_variables(
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
            self.config.save(self.layout.fpath_config)

    def run_main(self):
        """Install a pipeline config directory into the dataset."""
        # load the config and validate file contents (including file paths)
        pipeline_config = check_pipeline_bundle(
            self.dpath_pipeline,
            logger=self.logger,
            substitution_objs=[self, self.layout],  # to silence warnings
        )

        # generate destination path
        dpath_target = self.layout.get_dpath_pipeline_bundle(
            pipeline_config.PIPELINE_TYPE, pipeline_config.NAME, pipeline_config.VERSION
        )

        # check if the target directory already exists
        if dpath_target.exists():
            if not self.overwrite:
                raise FileExistsError(
                    f"Pipeline directory exists: {dpath_target}"
                    ". Use --overwrite to overwrite.",
                )
            else:
                self.rm(dpath_target, log_level=logging.DEBUG)

        # copy the directory
        self.copytree(
            path_source=self.dpath_pipeline,
            path_dest=dpath_target,
            log_level=logging.DEBUG,
        )

        # update global config with new pipeline variables
        self._add_variables_to_config(pipeline_config)

        self.logger.info(
            f"[{LogColor.SUCCESS}]Successfully installed pipeline "
            f"{pipeline_config.NAME}, version {pipeline_config.VERSION} "
            f"at {dpath_target}![/]"
        )
