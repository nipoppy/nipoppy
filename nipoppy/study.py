"""Study class."""

import json
from functools import cached_property
from pathlib import Path
from typing import Optional

from nipoppy.base import Base
from nipoppy.config.main import Config
from nipoppy.env import PROGRAM_NAME, StrOrPathLike
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils.utils import process_template_str


class Study(Base):
    """Representation of a Nipoppy study."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        fpath_layout: Optional[StrOrPathLike] = None,
        logger=None,
        verbose: bool = False,
    ):
        super().__init__()
        self.dpath_root = dpath_root
        self.fpath_layout = fpath_layout
        self.verbose = verbose

        self.logger = logger or get_logger(
            name=f"{PROGRAM_NAME}.{self.__class__.__name__}",
            verbose=verbose,
        )

    @cached_property
    def layout(self) -> DatasetLayout:
        """The layout object for this study."""
        return DatasetLayout(
            dpath_root=self.dpath_root,
            fpath_config=self.fpath_layout,
        )

    @cached_property
    def config(self) -> Config:
        """The main configuration object."""
        fpath_config = self.layout.fpath_config
        try:
            # load and apply user-defined substitutions
            self.logger.debug(f"Loading config from {fpath_config}")
            config = Config.load(fpath_config)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Config file not found: {self.layout.fpath_config}"
            )

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
        try:
            return Manifest.load(fpath_manifest)
        except FileNotFoundError:
            raise FileNotFoundError(f"Manifest file not found: {fpath_manifest}")

    @cached_property
    def curation_status_table(self) -> CurationStatusTable:
        """The curation status table."""
        fpath_table = self.layout.fpath_curation_status
        try:
            return CurationStatusTable.load(fpath_table)
        except FileNotFoundError:
            raise FileNotFoundError(f"Curation status file not found: {fpath_table}")

    @cached_property
    def processing_status_table(self) -> ProcessingStatusTable:
        """The processing status table."""
        fpath_table = self.layout.fpath_processing_status
        try:
            return ProcessingStatusTable.load(fpath_table)
        except FileNotFoundError:
            raise FileNotFoundError(f"Processing status file not found: {fpath_table}")
