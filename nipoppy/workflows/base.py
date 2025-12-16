"""Workflow utilities."""

from __future__ import annotations

import logging
import shlex
import subprocess
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Optional, Sequence

from nipoppy.base import Base
from nipoppy.env import EXT_LOG, StrOrPathLike
from nipoppy.exceptions import FileOperationError, ReturnCode
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.study import Study
from nipoppy.tabular.base import BaseTabular
from nipoppy.tabular.curation_status import (
    CurationStatusTable,
    generate_curation_status_table,
)
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils.utils import (
    add_path_timestamp,
    is_nipoppy_project,
    process_template_str,
)

logger = get_logger()


class BaseWorkflow(Base, ABC):
    """Base workflow class with logging/subprocess/filesystem utilities."""

    log_prefix_run = "[RUN]"
    log_prefix_run_stdout = "[RUN STDOUT]"
    log_prefix_run_stderr = "[RUN STDERR]"

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

    def log_command(self, command: str):
        """Write a command to the log with a special prefix."""
        # using extra={"markup": False} in case the command contains substrings
        # that would be interpreted as closing tags by the RichHandler
        logger.info(f"{self.log_prefix_run} {command}", extra={"markup": False})

    def run_command(
        self,
        command_or_args: Sequence[str] | str,
        check=True,
        quiet=False,
        **kwargs,
    ) -> subprocess.Popen | str:
        """Run a command in a subprocess.

        The command's stdout and stderr outputs are written to the log
        with special prefixes.

        If in "dry run" mode, the command is not executed, and the method returns
        the command string. Otherwise, the subprocess.Popen object is returned
        unless capture_output is True.

        Parameters
        ----------
        command_or_args : Sequence[str]  |  str
            The command to run.
        check : bool, optional
            If True, raise an error if the process exits with a non-zero code,
            by default True
        quiet : bool, optional
            If True, do not log the command, by default False
        **kwargs
            Passed to `subprocess.Popen`.

        Returns
        -------
        subprocess.Popen or str
        """

        def process_output(output_source, log_prefix: str, log_level=logging.INFO):
            """Consume lines from an IO stream and log them."""
            for line in output_source:
                line = line.strip("\n")
                # using extra={"markup": False} in case the output contains substrings
                # that would be interpreted as closing tags by the RichHandler
                logger.log(
                    level=log_level,
                    msg=f"{log_prefix} {line}",
                    extra={"markup": False},
                )

        # build command string
        if not isinstance(command_or_args, str):
            args = [str(arg) for arg in command_or_args]
            command = shlex.join(args)
        else:
            command = command_or_args
            args = shlex.split(command)

        # only pass a single string if shell is True
        if not kwargs.get("shell"):
            command_or_args = args

        if not quiet:
            self.log_command(command)

        if not self.dry_run:
            process = subprocess.Popen(
                command_or_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **kwargs,
            )

            while process.poll() is None:
                process_output(
                    process.stdout,
                    self.log_prefix_run_stdout,
                )

                process_output(
                    process.stderr,
                    self.log_prefix_run_stderr,
                    log_level=logging.ERROR,
                )

            if check and process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)

            run_output = process

        else:
            run_output = command

        return run_output

    def save_tabular_file(self, tabular: BaseTabular, fpath: Path):
        """Save a tabular file."""
        fpath_backup = tabular.save_with_backup(fpath, dry_run=self.dry_run)
        if fpath_backup is not None:
            logger.info(f"Saved to {fpath} (-> {fpath_backup})")
        else:
            logger.info(f"No changes to file at {fpath}")

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
        self.run_setup()
        self.run_main()
        self.run_cleanup()

    def copy_template(self, path_source, path_dest, **template_kwargs):
        """Copy a file with template substitution.

        Parameters
        ----------
        path_source
            Source template file path
        path_dest
            Destination file path
        **template_kwargs
            Keyword arguments passed to process_template_str for substitution
        """
        logger.debug(f"Copying template {path_source} to {path_dest}")
        if not self.dry_run:
            with open(path_source, "r") as f:
                content = process_template_str(f.read(), **template_kwargs)
            self.mkdir(Path(path_dest).parent)
            with open(path_dest, "w") as f:
                f.write(content)


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
                fpath_table_backup = table.save_with_backup(fpath_table)
                logger.info(
                    "Saved curation status table to "
                    f"{fpath_table} (-> {fpath_table_backup})"
                )
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
