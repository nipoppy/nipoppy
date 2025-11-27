"""Classes for loading configurations."""

from __future__ import annotations

import logging
import re
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Type

from pydantic import ValidationError

from nipoppy.config.boutiques import (
    BoutiquesConfig,
    get_boutiques_config_from_descriptor,
)
from nipoppy.config.hpc import HpcConfig
from nipoppy.config.pipeline import (
    BasePipelineConfig,
)
from nipoppy.config.tracker import TrackerConfig
from nipoppy.exceptions import (
    ConfigError,
    FileOperationError,
    WorkflowError,
)
from nipoppy.utils.utils import (
    load_json,
)

if TYPE_CHECKING:
    from nipoppy.env import PipelineTypeEnum
    from nipoppy.study import Study

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load configs for a pipeline."""

    def __init__(
        self,
        study: Study,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_step: str,
        pipeline_type: PipelineTypeEnum,
        pipeline_class: Type[BasePipelineConfig],
    ):
        self.study = study
        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version
        self.pipeline_step = pipeline_step
        self.pipeline_type = pipeline_type
        self.pipeline_class = pipeline_class

    @cached_property
    def dpath_pipeline_bundle(self) -> Path:
        """Path to the pipeline bundle directory."""
        return self.study.layout.get_dpath_pipeline_bundle(
            self.pipeline_type,
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
        )

    @cached_property
    def pipeline_config(self) -> BasePipelineConfig:
        """Get the user config object for the processing pipeline."""
        return self._get_pipeline_config(
            self.dpath_pipeline_bundle,
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            pipeline_class=self.pipeline_class,
        )

    @cached_property
    def pipeline_step_config(self):
        """Get the user config for the pipeline step."""
        return self.pipeline_config.get_step_config(step_name=self.pipeline_step)

    @cached_property
    def descriptor(self) -> dict:
        """Load the pipeline step's Boutiques descriptor."""
        if (fname_descriptor := self.pipeline_step_config.DESCRIPTOR_FILE) is None:
            raise ConfigError(
                "No descriptor file specified for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
        fpath_descriptor = self.dpath_pipeline_bundle / fname_descriptor
        logger.info(f"Loading descriptor from {fpath_descriptor}")
        descriptor = load_json(fpath_descriptor)
        descriptor = self.study.config.apply_pipeline_variables(
            pipeline_type=self.pipeline_config.PIPELINE_TYPE,
            pipeline_name=self.pipeline_config.NAME,
            pipeline_version=self.pipeline_config.VERSION,
            json_obj=descriptor,
        )
        return descriptor

    @cached_property
    def invocation(self) -> dict:
        """Load the pipeline step's Boutiques invocation."""
        if (fname_invocation := self.pipeline_step_config.INVOCATION_FILE) is None:
            raise ConfigError(
                "No invocation file specified for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
        fpath_invocation = self.dpath_pipeline_bundle / fname_invocation
        logger.info(f"Loading invocation from {fpath_invocation}")
        invocation = load_json(fpath_invocation)

        invocation = self.study.config.apply_pipeline_variables(
            pipeline_type=self.pipeline_config.PIPELINE_TYPE,
            pipeline_name=self.pipeline_config.NAME,
            pipeline_version=self.pipeline_config.VERSION,
            json_obj=invocation,
        )
        return invocation

    @cached_property
    def tracker_config(self) -> TrackerConfig:
        """Load the pipeline step's tracker configuration."""
        if (
            fname_tracker_config := self.pipeline_step_config.TRACKER_CONFIG_FILE
        ) is None:
            raise ConfigError(
                f"No tracker config file specified for pipeline {self.pipeline_name}"
                f" {self.pipeline_version}"
            )
        fpath_tracker_config = self.dpath_pipeline_bundle / fname_tracker_config
        logger.info(f"Loading tracker config from {fpath_tracker_config}")
        return TrackerConfig(**load_json(fpath_tracker_config))

    @cached_property
    def pybids_ignore_patterns(self) -> list[str]:
        """Load the pipeline step's PyBIDS ignore pattern list.

        Note: this does not apply any substitutions, since the subject/session
        patterns are always added.
        """
        # no file specified
        if (
            fname_pybids_ignore := self.pipeline_step_config.PYBIDS_IGNORE_FILE
        ) is None:
            return []

        fpath_pybids_ignore = self.dpath_pipeline_bundle / fname_pybids_ignore

        # load patterns from file
        logger.info(f"Loading PyBIDS ignore patterns from {fpath_pybids_ignore}")
        patterns = load_json(fpath_pybids_ignore)

        # validate format
        if not isinstance(patterns, list):
            raise ConfigError(
                f"Expected a list of strings in {fpath_pybids_ignore}"
                f", got {patterns} ({type(patterns)})"
            )

        return [re.compile(pattern) for pattern in patterns]

    @cached_property
    def hpc_config(self) -> HpcConfig:
        """Load the pipeline step's HPC configuration."""
        if (fname_hpc_config := self.pipeline_step_config.HPC_CONFIG_FILE) is None:
            data = {}
        else:
            fpath_hpc_config = self.dpath_pipeline_bundle / fname_hpc_config
            logger.info(f"Loading HPC config from {fpath_hpc_config}")
            data = self.study.process_template_json(load_json(fpath_hpc_config))
        return HpcConfig(**data)

    @cached_property
    def boutiques_config(self):
        """Get the Boutiques configuration."""
        try:
            boutiques_config = get_boutiques_config_from_descriptor(
                self.descriptor,
            )
        except ValidationError as e:
            error_message = str(e) + str(e.errors())
            raise WorkflowError(
                "Error when loading the Boutiques config from descriptor"
                f": {error_message}"
            )
        except ConfigError as e:
            logger.debug(
                "Caught exception when trying to load Boutiques config"
                f": {type(e).__name__}: {e}"
            )
            logger.debug(
                "Assuming Boutiques config is not in descriptor. Using default"
            )
            return BoutiquesConfig()

        logger.info(f"Loaded Boutiques config from descriptor: {boutiques_config}")
        return boutiques_config

    def _get_pipeline_config(
        self,
        dpath_pipeline_bundle: Path,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_class: Type[BasePipelineConfig],
    ) -> BasePipelineConfig:
        """Get the config for a pipeline."""
        fpath_config = dpath_pipeline_bundle / self.study.layout.fname_pipeline_config
        if not fpath_config.exists():
            raise FileOperationError(
                f"Pipeline config file not found at {fpath_config} for "
                f"pipeline: {pipeline_name} {pipeline_version}"
            )

        # NOTE: user-defined substitutions take precedence over the pipeline variables
        pipeline_config_json = self.study.config.apply_pipeline_variables(
            pipeline_type=self.pipeline_type,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            json_obj=self.study.process_template_json(
                load_json(fpath_config),
            ),
        )

        pipeline_config = pipeline_class(**pipeline_config_json)

        # make sure the config is for the correct pipeline
        if not (
            pipeline_config.NAME == pipeline_name
            and pipeline_config.VERSION == pipeline_version
        ):
            raise WorkflowError(
                f'Expected pipeline config to have NAME="{pipeline_name}" '
                f'and VERSION="{pipeline_version}", got "{pipeline_config.NAME}" and '
                f'"{pipeline_config.VERSION}" instead'
            )

        return self.study.config.propagate_container_config_to_pipeline(pipeline_config)
