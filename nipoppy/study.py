"""Study class."""

import json
from collections import defaultdict
from functools import cached_property
from pathlib import Path
from typing import Literal

from nipoppy.base import Base
from nipoppy.config.main import Config
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PipelineTypeEnum
from nipoppy.exceptions import ConfigError
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils.utils import load_json, process_template_str

logger = get_logger()


class Study(Base):
    """
    Representation of a Nipoppy study.

    This class is responsible for retrieving information about the study from disk based
    on paths defined in a DatasetLayout object. This includes configuration and tabular
    files.
    """

    def __init__(self, layout: DatasetLayout):
        """Representation of a Nipoppy study.

        Parameters
        ----------
        layout : DatasetLayout
            The dataset layout object.
        """
        super().__init__()
        self.layout = layout

    def __len__(self):
        """Get the number of unique participant-visit combinations in the study."""
        return len(self.manifest)

    @cached_property
    def config(self) -> Config:
        """The main configuration object."""
        fpath_config = self.layout.fpath_config
        # load and apply user-defined substitutions
        logger.debug(f"Loading config from {fpath_config}")
        config = Config.load(fpath_config)

        # replace path placeholders in the config
        # (except in the user-defined substitutions)
        user_substitutions = config.SUBSTITUTIONS  # stash original substitutions
        # this might modify the SUBSTITUTIONS field (which we don't want)
        config = Config(
            **json.loads(
                process_template_str(
                    config.model_dump_json(),
                    objs=[self.layout],
                )
            )
        )
        # restore original substitutions
        config.SUBSTITUTIONS = user_substitutions

        return config

    @cached_property
    def manifest(self) -> Manifest:
        """The manifest table."""
        fpath_manifest = Path(self.layout.fpath_manifest)
        logger.debug(f"Loading manifest from {fpath_manifest}")
        return Manifest.load(fpath_manifest)

    @cached_property
    def curation_status_table(self) -> CurationStatusTable:
        """The curation status table."""
        fpath_table = self.layout.fpath_curation_status
        logger.debug(f"Loading curation status table from {fpath_table}")
        return CurationStatusTable.load(fpath_table)

    @cached_property
    def processing_status_table(self) -> ProcessingStatusTable:
        """The processing status table."""
        fpath_table = self.layout.fpath_processing_status
        logger.debug(f"Loading processing status table from {fpath_table}")
        return ProcessingStatusTable.load(fpath_table)

    def _get_pipeline_info_map(
        self,
    ) -> dict[PipelineTypeEnum, defaultdict[str, list[str]]]:
        pipeline_type_to_info_map = {}
        for pipeline_type in PipelineTypeEnum:
            pipeline_names_to_versions_map = defaultdict(list)
            dpath_pipeline_bundles = (
                self.layout.dpath_pipelines
                / DatasetLayout.pipeline_type_to_dname_map[pipeline_type]
            )
            for fpath_config in sorted(
                dpath_pipeline_bundles.glob(f"*/{self.layout.fname_pipeline_config}")
            ):
                try:
                    pipeline_config = BasePipelineConfig(**load_json(fpath_config))
                except Exception as e:
                    raise ConfigError(
                        f"Error when loading pipeline config at {fpath_config}: {e}"
                    ) from e

                pipeline_names_to_versions_map[pipeline_config.NAME].append(
                    pipeline_config.VERSION
                )

            pipeline_type_to_info_map[pipeline_type] = pipeline_names_to_versions_map

        return pipeline_type_to_info_map

    def get_installed_pipelines(
        self, pipeline_type: Literal["bidsification", "processing", "extraction"]
    ) -> dict[str, list[str]]:
        """Get the name and version of installed pipelines.

        Parameters
        ----------
        pipeline_type : Literal["bidsification", "processing", "extraction"]

        Returns
        -------
        dict[str, list[str]]
            Dictionary mapping pipeline names to lists of available versions
            for the specified pipeline type.
        """
        try:
            pipeline_type_enum = PipelineTypeEnum(pipeline_type)
        except ValueError as exception:
            raise ValueError(
                f"Invalid pipeline type: {pipeline_type}. Must be one of: {[enum.value for enum in PipelineTypeEnum]}"  # noqa: E501
            ) from exception
        pipeline_type_to_info_map = self._get_pipeline_info_map()
        return dict(pipeline_type_to_info_map[pipeline_type_enum])
