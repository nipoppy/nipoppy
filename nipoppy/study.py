"""Study class."""

import json
from functools import cached_property
from logging import Logger
from pathlib import Path
from typing import Optional

from nipoppy.base import Base
from nipoppy.config.main import Config
from nipoppy.env import PROGRAM_NAME
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils.utils import process_template_str


class Study(Base):
    """
    Representation of a Nipoppy study.

    This class is responsible for retrieving information about the study from disk based
    on paths defined in a DatasetLayout object. This includes configuration and tabular
    files.
    """

    def __init__(
        self,
        layout: DatasetLayout,
        logger: Optional[Logger] = None,
        verbose: bool = False,
    ):
        """Representation of a Nipoppy study.

        Parameters
        ----------
        layout : DatasetLayout
            The dataset layout object.
        logger : Logger, optional
            Logger instance. If None (default), a new logger will be created.
        verbose : bool, optional
            Whether to enable verbose logging, by default False. Note: this is ignored
            if a custom logger is provided.
        """
        super().__init__()
        self.layout = layout
        self.verbose = verbose

        self.logger = logger or get_logger(
            name=f"{PROGRAM_NAME}.{self.__class__.__name__}",
            verbose=verbose,
        )

    @cached_property
    def config(self) -> Config:
        """The main configuration object."""
        fpath_config = self.layout.fpath_config
        # load and apply user-defined substitutions
        self.logger.debug(f"Loading config from {fpath_config}")
        config = Config.load(fpath_config)

        # replace path placeholders in the config
        # (except in the user-defined substitutions)
        user_substitutions = config.SUBSTITUTIONS  # stash original substitutions
        # this might modify the SUBSTITUTIONS field (which we don't want)
        config = Config(
            **json.loads(
                process_template_str(
                    config.model_dump_json(),
                    objs=[self, self.layout],
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
        self.logger.debug(f"Loading manifest from {fpath_manifest}")
        return Manifest.load(fpath_manifest)

    @cached_property
    def curation_status_table(self) -> CurationStatusTable:
        """The curation status table."""
        fpath_table = self.layout.fpath_curation_status
        self.logger.debug(f"Loading curation status table from {fpath_table}")
        return CurationStatusTable.load(fpath_table)

    @cached_property
    def processing_status_table(self) -> ProcessingStatusTable:
        """The processing status table."""
        fpath_table = self.layout.fpath_processing_status
        self.logger.debug(f"Loading processing status table from {fpath_table}")
        return ProcessingStatusTable.load(fpath_table)
