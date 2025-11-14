"""Configuration loading functionality for pipeline workflows."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Type

from pydantic import ValidationError

from nipoppy.config.boutiques import (
    BoutiquesConfig,
    get_boutiques_config_from_descriptor,
)
from nipoppy.config.hpc import HpcConfig
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.utils.bids import (
    participant_id_to_bids_participant_id,
    session_id_to_bids_session_id,
)
from nipoppy.utils.utils import (
    apply_substitutions_to_json,
    load_json,
    process_template_str,
)

if TYPE_CHECKING:
    from nipoppy.config.main import Config
    from nipoppy.layout import DatasetLayout
    from nipoppy.logger import NipoppyLogger


class PipelineConfigLoader:
    """Handles loading and processing of pipeline configuration files."""

    def __init__(
        self,
        layout: DatasetLayout,
        logger: NipoppyLogger,
        config: Config,
        dpath_pipeline_bundle: Path,
        process_template_json_callback: callable = None,
    ):
        """Initialize the config loader.

        Parameters
        ----------
        layout : DatasetLayout
            Dataset layout object
        logger : NipoppyLogger
            Logger instance
        config : Config
            Main dataset configuration
        dpath_pipeline_bundle : Path
            Path to pipeline bundle directory
        process_template_json_callback : callable, optional
            Callback function for template processing. If None, uses internal method.
        """
        self.layout = layout
        self.logger = logger
        self.config = config
        self.dpath_pipeline_bundle = dpath_pipeline_bundle
        self._process_template_json_callback = process_template_json_callback

    def process_template_json(
        self,
        template_json: dict,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        bids_participant_id: Optional[str] = None,
        bids_session_id: Optional[str] = None,
        objs: Optional[list] = None,
        return_str: bool = False,
        with_substitutions: bool = True,
        **kwargs,
    ):
        """Replace template strings in a JSON object.

        Parameters
        ----------
        template_json : dict
            JSON object with template strings
        participant_id : str, optional
            Participant ID
        session_id : str, optional
            Session ID
        bids_participant_id : str, optional
            BIDS-formatted participant ID
        bids_session_id : str, optional
            BIDS-formatted session ID
        objs : list, optional
            Additional objects for template processing
        return_str : bool
            If True, return as string instead of dict
        with_substitutions : bool
            If True, apply user-defined substitutions
        **kwargs
            Additional keyword arguments for template processing

        Returns
        -------
        dict or str
            Processed JSON object or string
        """
        # Use callback if provided (for backward compatibility)
        if self._process_template_json_callback is not None:
            return self._process_template_json_callback(
                template_json=template_json,
                participant_id=participant_id,
                session_id=session_id,
                bids_participant_id=bids_participant_id,
                bids_session_id=bids_session_id,
                objs=objs,
                return_str=return_str,
                with_substitutions=with_substitutions,
                **kwargs,
            )
        
        # Default implementation
        if with_substitutions:
            # apply user-defined substitutions to maintain compatibility with older
            # pipeline config files that do not use the new pipeline variables
            template_json = apply_substitutions_to_json(
                template_json, self.config.SUBSTITUTIONS
            )
        if participant_id is not None:
            if bids_participant_id is None:
                bids_participant_id = participant_id_to_bids_participant_id(
                    participant_id
                )
            kwargs["participant_id"] = participant_id
            kwargs["bids_participant_id"] = bids_participant_id

        if session_id is not None:
            if bids_session_id is None:
                bids_session_id = session_id_to_bids_session_id(session_id)
            kwargs["session_id"] = session_id
            kwargs["bids_session_id"] = bids_session_id

        if objs is None:
            objs = []
        objs.append(self.layout)

        if kwargs:
            self.logger.debug("Available replacement strings: ")
            max_len = max(len(k) for k in kwargs)
            for k, v in kwargs.items():
                self.logger.debug(f"\t{k}:".ljust(max_len + 3) + v)
            self.logger.debug(f"\t+ all attributes in: {objs}")

        template_json_str = process_template_str(
            json.dumps(template_json),
            objs=objs,
            **kwargs,
        )

        return template_json_str if return_str else json.loads(template_json_str)

    def load_pipeline_config(
        self,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_type: str,
        pipeline_class: Type[BasePipelineConfig],
    ) -> BasePipelineConfig:
        """Load and validate pipeline configuration.

        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline
        pipeline_version : str
            Version of the pipeline
        pipeline_type : str
            Type of pipeline
        pipeline_class : Type[BasePipelineConfig]
            Pipeline config class to instantiate

        Returns
        -------
        BasePipelineConfig
            Validated pipeline configuration

        Raises
        ------
        FileNotFoundError
            If config file doesn't exist
        RuntimeError
            If config NAME/VERSION don't match expected values
        """
        fpath_config = self.dpath_pipeline_bundle / self.layout.fname_pipeline_config
        if not fpath_config.exists():
            raise FileNotFoundError(
                f"Pipeline config file not found at {fpath_config} for "
                f"pipeline: {pipeline_name} {pipeline_version}"
            )

        # NOTE: user-defined substitutions take precedence over the pipeline variables
        pipeline_config_json = self.config.apply_pipeline_variables(
            pipeline_type=pipeline_type,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            json_obj=self.process_template_json(
                load_json(fpath_config),
            ),
        )

        pipeline_config = pipeline_class(**pipeline_config_json)

        # make sure the config is for the correct pipeline
        if not (
            pipeline_config.NAME == pipeline_name
            and pipeline_config.VERSION == pipeline_version
        ):
            raise RuntimeError(
                f'Expected pipeline config to have NAME="{pipeline_name}" '
                f'and VERSION="{pipeline_version}", got "{pipeline_config.NAME}" and '
                f'"{pipeline_config.VERSION}" instead'
            )

        return self.config.propagate_container_config_to_pipeline(pipeline_config)

    def load_descriptor(
        self, fname_descriptor: str, pipeline_type: str, pipeline_name: str, pipeline_version: str
    ) -> dict:
        """Load Boutiques descriptor.

        Parameters
        ----------
        fname_descriptor : str
            Descriptor filename
        pipeline_type : str
            Type of pipeline
        pipeline_name : str
            Name of the pipeline
        pipeline_version : str
            Version of the pipeline

        Returns
        -------
        dict
            Boutiques descriptor

        Raises
        ------
        ValueError
            If descriptor file is not specified
        """
        if fname_descriptor is None:
            raise ValueError(
                "No descriptor file specified for pipeline"
                f" {pipeline_name} {pipeline_version}"
            )
        fpath_descriptor = self.dpath_pipeline_bundle / fname_descriptor
        self.logger.info(f"Loading descriptor from {fpath_descriptor}")
        descriptor = load_json(fpath_descriptor)
        descriptor = self.config.apply_pipeline_variables(
            pipeline_type=pipeline_type,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            json_obj=descriptor,
        )
        return descriptor

    def load_invocation(
        self, fname_invocation: str, pipeline_type: str, pipeline_name: str, pipeline_version: str
    ) -> dict:
        """Load Boutiques invocation.

        Parameters
        ----------
        fname_invocation : str
            Invocation filename
        pipeline_type : str
            Type of pipeline
        pipeline_name : str
            Name of the pipeline
        pipeline_version : str
            Version of the pipeline

        Returns
        -------
        dict
            Boutiques invocation

        Raises
        ------
        ValueError
            If invocation file is not specified
        """
        if fname_invocation is None:
            raise ValueError(
                "No invocation file specified for pipeline"
                f" {pipeline_name} {pipeline_version}"
            )
        fpath_invocation = self.dpath_pipeline_bundle / fname_invocation
        self.logger.info(f"Loading invocation from {fpath_invocation}")
        invocation = load_json(fpath_invocation)

        invocation = self.config.apply_pipeline_variables(
            pipeline_type=pipeline_type,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            json_obj=invocation,
        )
        return invocation

    def load_tracker_config(self, fname_tracker_config: str, pipeline_name: str, pipeline_version: str) -> TrackerConfig:
        """Load tracker configuration.

        Parameters
        ----------
        fname_tracker_config : str
            Tracker config filename
        pipeline_name : str
            Name of the pipeline
        pipeline_version : str
            Version of the pipeline

        Returns
        -------
        TrackerConfig
            Tracker configuration

        Raises
        ------
        ValueError
            If tracker config file is not specified
        """
        if fname_tracker_config is None:
            raise ValueError(
                f"No tracker config file specified for pipeline {pipeline_name}"
                f" {pipeline_version}"
            )
        fpath_tracker_config = self.dpath_pipeline_bundle / fname_tracker_config
        self.logger.info(f"Loading tracker config from {fpath_tracker_config}")
        return TrackerConfig(**load_json(fpath_tracker_config))

    def load_pybids_ignore_patterns(self, fname_pybids_ignore: Optional[str]) -> list[re.Pattern]:
        """Load PyBIDS ignore patterns.

        Parameters
        ----------
        fname_pybids_ignore : str, optional
            PyBIDS ignore patterns filename

        Returns
        -------
        list[re.Pattern]
            Compiled regex patterns
        """
        # no file specified
        if fname_pybids_ignore is None:
            return []

        fpath_pybids_ignore = self.dpath_pipeline_bundle / fname_pybids_ignore

        # load patterns from file
        self.logger.info(f"Loading PyBIDS ignore patterns from {fpath_pybids_ignore}")
        patterns = load_json(fpath_pybids_ignore)

        # validate format
        if not isinstance(patterns, list):
            raise ValueError(
                f"Expected a list of strings in {fpath_pybids_ignore}"
                f", got {patterns} ({type(patterns)})"
            )

        return [re.compile(pattern) for pattern in patterns]

    def load_hpc_config(self, fname_hpc_config: Optional[str]) -> HpcConfig:
        """Load HPC configuration.

        Parameters
        ----------
        fname_hpc_config : str, optional
            HPC config filename

        Returns
        -------
        HpcConfig
            HPC configuration
        """
        if fname_hpc_config is None:
            data = {}
        else:
            fpath_hpc_config = self.dpath_pipeline_bundle / fname_hpc_config
            self.logger.info(f"Loading HPC config from {fpath_hpc_config}")
            data = self.process_template_json(load_json(fpath_hpc_config))
        return HpcConfig(**data)

    def load_boutiques_config(self, descriptor: dict) -> BoutiquesConfig:
        """Load Boutiques configuration from descriptor.

        Parameters
        ----------
        descriptor : dict
            Boutiques descriptor

        Returns
        -------
        BoutiquesConfig
            Boutiques configuration
        """
        try:
            boutiques_config = get_boutiques_config_from_descriptor(descriptor)
        except ValidationError as exception:
            error_message = str(exception) + str(exception.errors())
            raise ValueError(
                f"Error when loading the Boutiques config from descriptor"
                f": {error_message}"
            )
        except RuntimeError as exception:
            self.logger.debug(
                "Caught exception when trying to load Boutiques config"
                f": {type(exception).__name__}: {exception}"
            )
            self.logger.debug(
                "Assuming Boutiques config is not in descriptor. Using default"
            )
            return BoutiquesConfig()

        self.logger.info(f"Loaded Boutiques config from descriptor: {boutiques_config}")
        return boutiques_config
