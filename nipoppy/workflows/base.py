"""Workflow utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Optional

from nipoppy.base import Base
from nipoppy.env import EXT_LOG, StrOrPathLike
from nipoppy.exceptions import FileOperationError, ReturnCode
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.study import Study
from nipoppy.tabular.curation_status import (
    CurationStatusTable,
    generate_curation_status_table,
)
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils.utils import (
    add_path_timestamp,
    is_nipoppy_project,
)

logger = get_logger()


class BaseWorkflow(Base, ABC):
    """Base workflow class with logging/subprocess/filesystem utilities."""

    def __init__(self, name: str, verbose: bool = False, dry_run: bool = False):
        """Initialize the workflow instance.

        Parameters
        ----------
        name : str
            Name of the workflow, used for logging.
        verbose : bool, optional
            If True, set the logger to DEBUG level, by default False
        dry_run : bool, optional
            If True, print commands without executing them, by default False
        """
        self.name = name
        self.dry_run = dry_run
        self.verbose = verbose

        # for the CLI
        self.return_code = ReturnCode.SUCCESS

        logger.set_verbose(self.verbose)

    def run_setup(self):
        """Run the setup part of the workflow."""
        logger.debug(self)
        if self.dry_run:
            logger.info("Doing a dry run")

    @abstractmethod
    def run_main(self):
        """Run the main part of the workflow."""
        pass

    def run_cleanup(self):
        """Run the cleanup part of the workflow."""
        pass

    def run(self):
        """Run the workflow."""
        try:
            self.run_setup()
            self.run_main()
        except Exception:
            raise
        finally:
            self.run_cleanup()


class BaseDatasetWorkflow(BaseWorkflow, ABC):
    """Base workflow class with awareness of dataset layout and components."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        name: str,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
        _skip_logfile: bool = False,
        _validate_layout: bool = True,
    ):
        """Initialize the workflow instance.

        Parameters
        ----------
        dpath_root : nipoppy.env.StrOrPathLike
            Path the the root directory of the dataset.
        name : str
            Name of the workflow, used for logging.
        fpath_layout : nipoppy.env.StrOrPathLike, optional
            Path to a custom layout file, by default None
        verbose : bool, optional
            If True, set the logger to DEBUG level, by default False
        dry_run : bool, optional
            If True, print commands without executing them, by default False
        _skip_logfile : bool, optional
            If True, do not write log to file, by default False
        _validate_layout : bool, optional
            If True, validate the layout during setup, by default True
        """
        super().__init__(name=name, verbose=verbose, dry_run=dry_run)

        # `.nipoppy` is not created by default in version 0.3.4 and below
        self.dpath_root = is_nipoppy_project(dpath_root) or Path(dpath_root)
        self.fpath_layout = fpath_layout
        self._skip_logfile = _skip_logfile
        self._validate_layout = _validate_layout

        self.study = Study(
            DatasetLayout(
                dpath_root=self.dpath_root,
                fpath_config=self.fpath_layout,
            )
        )

    def generate_fpath_log(
        self,
        dnames_parent: Optional[str | list[str]] = None,
        fname_stem: Optional[str] = None,
    ) -> Path:
        """Generate a log file path."""
        if dnames_parent is None:
            dnames_parent = []
        if isinstance(dnames_parent, str):
            dnames_parent = [dnames_parent]
        if fname_stem is None:
            fname_stem = self.name
        dpath_log = self.study.layout.dpath_logs / self.name
        for dname in dnames_parent:
            dpath_log = dpath_log / dname
        return dpath_log / add_path_timestamp(f"{fname_stem}{EXT_LOG}")

    def run_setup(self):
        """Run the setup part of the workflow."""
        if self._validate_layout:
            self.study.layout.validate()

        if not self._skip_logfile:
            logger.add_file_handler(self.generate_fpath_log())

        super().run_setup()

    @cached_property
    def curation_status_table(self) -> CurationStatusTable:
        """
        Load the curation status file if it exists.

        Otherwise, generate a new one.
        """
        fpath_table = Path(self.study.layout.fpath_curation_status)
        try:
            return self.study.curation_status_table
        except FileNotFoundError:
            logger.warning(
                f"Curation status file not found: {fpath_table}"
                ". Generating a new one on-the-fly"
            )
            table = generate_curation_status_table(
                manifest=self.study.manifest,
                dicom_dir_map=self.dicom_dir_map,
                dpath_downloaded=self.study.layout.dpath_pre_reorg,
                dpath_organized=self.study.layout.dpath_post_reorg,
                dpath_bidsified=self.study.layout.dpath_bids,
                empty=False,
            )

            if not self.dry_run:
                table.save_with_backup(fpath_table)
            else:
                logger.info(
                    "Not writing curation status table to "
                    f"{fpath_table} since this is a dry run"
                )

            return table

    @cached_property
    def processing_status_table(self) -> ProcessingStatusTable:
        """
        Load the processing status file it it exists.

        Otherwise, return an empty processing status table.
        """
        try:
            return self.study.processing_status_table
        except FileNotFoundError:
            return ProcessingStatusTable()

    @cached_property
    def dicom_dir_map(self) -> DicomDirMap:
        """Get the DICOM directory mapping."""
        fpath_dicom_dir_map = self.study.config.DICOM_DIR_MAP_FILE
        if fpath_dicom_dir_map is not None and not Path(fpath_dicom_dir_map).exists():
            raise FileOperationError(
                f"DICOM directory map file not found: {fpath_dicom_dir_map}"
            )

        return DicomDirMap.load_or_generate(
            manifest=self.study.manifest,
            fpath_dicom_dir_map=fpath_dicom_dir_map,
            participant_first=self.study.config.DICOM_DIR_PARTICIPANT_FIRST,
        )
