"""Workflow utilities."""
import datetime
import logging
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence

from nipoppy.base import _Base
from nipoppy.layout import DatasetLayout
from nipoppy.logger import get_logger

LOG_SUFFIX = ".log"


class _Workflow(_Base, ABC):
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

    def generate_fpath_log(self) -> Path:
        """Generate a log file path."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dpath_log = self.layout.dpath_logs / self.name
        fname_log = f"{self.path_sep.join([self.name, timestamp])}{LOG_SUFFIX}"
        return dpath_log / fname_log

    def log_command(self, command: str):
        """Write a command to the log with a special prefix."""
        self.logger.info(f"{self.log_prefix_run} {command}")

    def run_command(
        self,
        command_or_args: Sequence[str] | str,
        shell=False,
        check=True,
        capture_output=False,
        **kwargs,
    ) -> subprocess.Popen | tuple[str, str] | str:
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
        shell : bool, optional
            Passed to `subprocess.Popen`, by default False
        check : bool, optional
            If True, raise an error if the process exits with a non-zero code,
            by default True
        capture_output : bool, optional
            If True, return a tuple of strings from stdout and stderr, by default False
        **kwargs
            Passed to `subprocess.Popen`.

        Returns
        -------
        subprocess.Popen | tuple[str, str] | str
        """

        def process_output(output_source, output_str: str, log_prefix: str):
            """Consume lines from an IO stream and append them to a string."""
            for line in output_source:
                if capture_output:
                    output_str += line  # store the line as-is
                line = line.strip("\n")
                self.logger.debug(f"{log_prefix} {line}")
            return output_str

        # build command string
        if not isinstance(command_or_args, str):
            args = [str(arg) for arg in command_or_args]
            command = shlex.join(args)
        else:
            command = command_or_args
            args = shlex.split(command)

        # only pass a single string if shell is True
        if not shell:
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
                shell=shell,
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
                self.logger.error(exception)
                raise exception

            run_output = process

        else:
            run_output = command

        # return the captured stdout/stderr strings
        # instead of the Popen object or command string
        if capture_output:
            run_output = (stdout_str, stderr_str)

        return run_output

    def run_setup(self, **kwargs):
        """Run the setup part of the workflow."""
        self.logger.info(f"========== BEGIN {self.name.upper()} ==========")
        self.logger.info(self)
        if self.dry_run:
            self.logger.info(
                f"Doing a dry run: {self.log_prefix_run} commands will not be executed"
            )

    @abstractmethod
    def run_main(self, **kwargs):
        """Run the main part of the workflow."""
        pass

    def run_cleanup(self, **kwargs):
        """Run the cleanup part of the workflow."""
        self.logger.info(f"========== END {self.name.upper()} ==========")

    def run(self, **kwargs):
        """Run the workflow."""
        self.run_setup(**kwargs)
        self.run_main(**kwargs)
        self.run_cleanup(**kwargs)
