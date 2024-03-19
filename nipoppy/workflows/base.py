"""Workflow utilities."""

import datetime
import logging
import shlex
import subprocess
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Optional, Sequence

from nipoppy.base import Base
from nipoppy.config.base import Config
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger
from nipoppy.tabular.base import BaseTabular
from nipoppy.tabular.doughnut import Doughnut, generate_doughnut
from nipoppy.tabular.manifest import Manifest

LOG_SUFFIX = ".log"


class BaseWorkflow(Base, ABC):
    """Base class with logging/subprocess utilities."""

    path_sep = "-"
    log_prefix_run = "[RUN]"
    log_prefix_run_stdout = "[RUN STDOUT]"
    log_prefix_run_stderr = "[RUN STDERR]"

    def __init__(
        self,
        dpath_root: Path | str,
        name: str,
        logger: Optional[logging.Logger] = None,
        dry_run=False,
    ):
        """Initialize the workflow instance.

        Parameters
        ----------
        dpath_root : Path | str
            Path the the root directory of the dataset.
        name : str
            Name of the workflow, used for logging.
        logger : logging.Logger, optional
            Logger, by default None
        dry_run : bool, optional
            If True, print commands without executing them, by default False
        """
        if logger is None:
            logger = get_logger(name=name)

        self.dpath_root = Path(dpath_root)
        self.name = name
        self.logger = logger
        self.dry_run = dry_run

        self.layout = DatasetLayout(self.dpath_root)

    def generate_fpath_log(
        self,
        dname_parent: Optional[list[str]] = None,
        fname_stem: Optional[str] = None,
    ) -> Path:
        """Generate a log file path."""
        if dname_parent is None:
            dname_parent = []
        if isinstance(dname_parent, str):
            dname_parent = [dname_parent]
        if fname_stem is None:
            fname_stem = self.name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dpath_log = self.layout.dpath_logs / self.name
        for dname in dname_parent:
            dpath_log = dpath_log / dname
        fname_log = f"{self.path_sep.join([fname_stem, timestamp])}{LOG_SUFFIX}"
        return dpath_log / fname_log

    def log_command(self, command: str):
        """Write a command to the log with a special prefix."""
        self.logger.info(f"{self.log_prefix_run} {command}")

    def run_command(
        self,
        command_or_args: Sequence[str] | str,
        check=True,
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
        command_or_args : Sequence[str] | str
            The command to run.
        check : bool, optional
            If True, raise an error if the process exits with a non-zero code,
            by default True
        **kwargs
            Passed to `subprocess.Popen`.

        Returns
        -------
        subprocess.Popen | str
        """

        def process_output(output_source, output_str: str, log_prefix: str):
            """Consume lines from an IO stream and append them to a string."""
            for line in output_source:
                line = line.strip("\n")
                self.logger.info(f"{log_prefix} {line}")
            return output_str

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

        self.log_command(command)

        stdout_str = ""
        stderr_str = ""
        if not self.dry_run:
            process = subprocess.Popen(
                command_or_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **kwargs,
            )

            while process.poll() is None:
                stdout_str = process_output(
                    process.stdout,
                    stdout_str,
                    self.log_prefix_run_stdout,
                )

                stderr_str = process_output(
                    process.stderr,
                    stderr_str,
                    self.log_prefix_run_stderr,
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
        if not self.dry_run:
            fpath_doughnut_backup = tabular.save_with_backup(fpath)
            if fpath_doughnut_backup is not None:
                self.logger.info(f"Saved to {fpath} (-> {fpath_doughnut_backup})")
            else:
                self.logger.info(f"No changes to file at {fpath}")
        else:
            self.logger.info(f"Not writing to {fpath} since this is a dry run")

    def run_setup(self, **kwargs):
        """Run the setup part of the workflow."""
        self.logger.info(f"========== BEGIN {self.name.upper()} WORKFLOW ==========")
        self.logger.info(self)
        if self.dry_run:
            self.logger.info("Doing a dry run")

    @abstractmethod
    def run_main(self, **kwargs):
        """Run the main part of the workflow."""
        pass

    def run_cleanup(self, **kwargs):
        """Run the cleanup part of the workflow."""
        self.logger.info(f"========== END {self.name.upper()} WORKFLOW ==========")

    def run(self, **kwargs):
        """Run the workflow."""
        self.run_setup(**kwargs)
        self.run_main(**kwargs)
        self.run_cleanup(**kwargs)

    @cached_property
    def config(self) -> Config:
        """Load the configuration."""
        fpath_config = self.layout.fpath_config
        try:
            self.logger.info(f"Loading config from {fpath_config}")
            return Config.load(fpath_config)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Config file not found: {self.layout.fpath_config}"
            )

    @cached_property
    def manifest(self) -> Manifest:
        """Load the manifest."""
        fpath_manifest = self.layout.fpath_manifest
        expected_sessions = self.config.SESSIONS
        expected_visits = self.config.VISITS
        try:
            return Manifest.load(
                fpath_manifest,
                sessions=expected_sessions,
                visits=expected_visits,
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Manifest file not found: {fpath_manifest}")

    @cached_property
    def doughnut(self) -> Doughnut:
        """Load the doughnut."""
        logger = self.logger
        fpath_doughnut = self.layout.fpath_doughnut
        try:
            return Doughnut.load(fpath_doughnut)
        except FileNotFoundError:
            self.logger.warning(
                f"Doughnut file not found: {fpath_doughnut}"
                ". Generating a new one on-the-fly"
            )
            doughnut = generate_doughnut(
                manifest=self.manifest,
                dpath_downloaded=self.layout.dpath_raw_dicom,
                dpath_organized=self.layout.dpath_dicom,
                dpath_converted=self.layout.dpath_bids,
                empty=False,
                logger=self.logger,
            )

            if not self.dry_run:
                fpath_doughnut_backup = doughnut.save_with_backup(fpath_doughnut)
                logger.info(
                    f"Saved doughnut to {fpath_doughnut} (-> {fpath_doughnut_backup})"
                )
            else:
                logger.info(
                    f"Not writing doughnut to {fpath_doughnut} since this is a dry run"
                )

            return doughnut
