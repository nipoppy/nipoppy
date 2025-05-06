"""Workflow utilities."""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Optional, Sequence

from nipoppy.base import Base
from nipoppy.config.main import Config
from nipoppy.env import EXT_LOG, PROGRAM_NAME, ReturnCode, StrOrPathLike
from nipoppy.layout import DatasetLayout
from nipoppy.logger import add_logfile, capture_warnings, get_logger
from nipoppy.tabular.base import BaseTabular
from nipoppy.tabular.curation_status import (
    CurationStatusTable,
    generate_curation_status_table,
)
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils import add_path_timestamp, process_template_str


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
        self.verbose = verbose
        self.dry_run = dry_run

        # for the CLI
        self.return_code = ReturnCode.SUCCESS

        # set up logging
        log_level = logging.DEBUG if verbose else logging.INFO
        self.logger = get_logger(
            name=f"{PROGRAM_NAME}.{self.__class__.__name__}",
            level=log_level,
        )
        logging.captureWarnings(True)
        capture_warnings(self.logger)

    def log_command(self, command: str):
        """Write a command to the log with a special prefix."""
        # using extra={"markup": False} in case the command contains substrings
        # that would be interpreted as closing tags by the RichHandler
        self.logger.info(f"{self.log_prefix_run} {command}", extra={"markup": False})

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
                line = line.decode()
                if "\r" in line:
                    continue
                line = line.strip("\n")
                # using extra={"markup": False} in case the output contains substrings
                # that would be interpreted as closing tags by the RichHandler
                self.logger.log(
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
                exception = subprocess.CalledProcessError(process.returncode, command)
                raise exception

            run_output = process

        else:
            run_output = command

        return run_output

    def save_tabular_file(self, tabular: BaseTabular, fpath: Path):
        """Save a tabular file."""
        fpath_backup = tabular.save_with_backup(fpath, dry_run=self.dry_run)
        if fpath_backup is not None:
            self.logger.info(f"Saved to {fpath} (-> {fpath_backup})")
        else:
            self.logger.info(f"No changes to file at {fpath}")

    def run_setup(self):
        """Run the setup part of the workflow."""
        self.logger.info(f"========== BEGIN {self.name.upper()} WORKFLOW ==========")
        self.logger.info(self)
        if self.dry_run:
            self.logger.info("Doing a dry run")

    @abstractmethod
    def run_main(self):
        """Run the main part of the workflow."""
        pass

    def run_cleanup(self):
        """Run the cleanup part of the workflow."""
        self.logger.info(f"========== END {self.name.upper()} WORKFLOW ==========")

    def run(self):
        """Run the workflow."""
        self.run_setup()
        self.run_main()
        self.run_cleanup()

    def mkdir(self, dpath, log_level=logging.INFO, **kwargs):
        """
        Create a directory (by default including parents).

        Do nothing if the directory already exists.
        """
        kwargs_to_use = {"parents": True, "exist_ok": True}
        kwargs_to_use.update(kwargs)

        dpath = Path(dpath)

        if not dpath.exists():
            self.logger.log(level=log_level, msg=f"Creating directory {dpath}")
            if not self.dry_run:
                dpath.mkdir(**kwargs_to_use)
        elif not dpath.is_dir():
            raise FileExistsError(
                f"Path already exists but is not a directory: {dpath}"
            )

    def copy(self, path_source, path_dest, log_level=logging.INFO, **kwargs):
        """Copy a file or directory."""
        self.logger.log(level=log_level, msg=f"Copying {path_source} to {path_dest}")
        if not self.dry_run:
            shutil.copy2(src=path_source, dst=path_dest, **kwargs)

    def copytree(self, path_source, path_dest, log_level=logging.INFO, **kwargs):
        """Copy directory tree."""
        self.logger.log(level=log_level, msg=f"Copying {path_source} to {path_dest}")
        if not self.dry_run:
            shutil.copytree(src=path_source, dst=path_dest, **kwargs)

    def movetree(
        self,
        path_source,
        path_dest,
        kwargs_mkdir=None,
        kwargs_move=None,
        log_level=logging.INFO,
    ):
        """Move directory tree."""
        kwargs_mkdir = kwargs_mkdir or {}
        kwargs_move = kwargs_move or {}
        self.logger.log(level=log_level, msg=f"Moving {path_source} to {path_dest}")
        if not self.dry_run:
            self.mkdir(path_dest, log_level=log_level, **kwargs_mkdir)
            file_names = os.listdir(path_source)
            for file_name in file_names:
                shutil.move(
                    src=os.path.join(path_source, file_name),
                    dst=path_dest,
                    **kwargs_move,
                )
            Path(path_source).rmdir()

    def create_symlink(self, path_source, path_dest, log_level=logging.INFO, **kwargs):
        """Create a symlink to another path."""
        self.logger.log(
            level=log_level,
            msg=f"Creating a symlink from {path_source} to {path_dest}",
        )
        if not self.dry_run:
            os.symlink(path_source, path_dest, **kwargs)

    def rm(self, path, log_level=logging.INFO, **kwargs):
        """Remove a file or directory."""
        kwargs_to_use = {"ignore_errors": True}
        kwargs_to_use.update(kwargs)
        self.logger.log(level=log_level, msg=f"Removing {path}")
        if not self.dry_run:
            shutil.rmtree(path, **kwargs_to_use)


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

        self.dpath_root = Path(dpath_root)
        self.fpath_layout = fpath_layout
        self._skip_logfile = _skip_logfile
        self._validate_layout = _validate_layout

        self.layout = DatasetLayout(dpath_root=dpath_root, fpath_config=fpath_layout)

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
        dpath_log = self.layout.dpath_logs / self.name
        for dname in dnames_parent:
            dpath_log = dpath_log / dname
        return dpath_log / add_path_timestamp(f"{fname_stem}{EXT_LOG}")

    def run_setup(self):
        """Run the setup part of the workflow."""
        if not self._skip_logfile:
            add_logfile(self.logger, self.generate_fpath_log())

        super().run_setup()

        if self._validate_layout:
            self.layout.validate()

    @cached_property
    def config(self) -> Config:
        """
        Load the configuration.

        Raise error if not found.
        """
        fpath_config = self.layout.fpath_config
        try:
            # load and apply user-defined substitutions
            self.logger.info(f"Loading config from {fpath_config}")
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
        """
        Load the manifest.

        Raise error if not found.
        """
        fpath_manifest = Path(self.layout.fpath_manifest)
        try:
            return Manifest.load(fpath_manifest)
        except FileNotFoundError:
            raise FileNotFoundError(f"Manifest file not found: {fpath_manifest}")

    @cached_property
    def curation_status_table(self) -> CurationStatusTable:
        """
        Load the curation status file if it exists.

        Otherwise, generate a new one.
        """
        logger = self.logger
        fpath_table = Path(self.layout.fpath_curation_status)
        try:
            return CurationStatusTable.load(fpath_table)
        except FileNotFoundError:
            self.logger.warning(
                f"Curation status file not found: {fpath_table}"
                ". Generating a new one on-the-fly"
            )
            table = generate_curation_status_table(
                manifest=self.manifest,
                dicom_dir_map=self.dicom_dir_map,
                dpath_downloaded=self.layout.dpath_pre_reorg,
                dpath_organized=self.layout.dpath_post_reorg,
                dpath_bidsified=self.layout.dpath_bids,
                empty=False,
                logger=self.logger,
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
            return ProcessingStatusTable.load(self.layout.fpath_processing_status)
        except FileNotFoundError:
            return ProcessingStatusTable()

    @cached_property
    def dicom_dir_map(self) -> DicomDirMap:
        """Get the DICOM directory mapping."""
        fpath_dicom_dir_map = self.config.DICOM_DIR_MAP_FILE
        if fpath_dicom_dir_map is not None and not Path(fpath_dicom_dir_map).exists():
            raise FileNotFoundError(
                "DICOM directory map file not found" f": {fpath_dicom_dir_map}"
            )

        return DicomDirMap.load_or_generate(
            manifest=self.manifest,
            fpath_dicom_dir_map=fpath_dicom_dir_map,
            participant_first=self.config.DICOM_DIR_PARTICIPANT_FIRST,
        )
