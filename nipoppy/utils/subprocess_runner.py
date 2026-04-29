"""Subprocess runner utilities with streaming log output and dry-run support."""

from __future__ import annotations

import logging
import shlex
import subprocess
from typing import Protocol, Sequence

from nipoppy.logger import get_logger

logger = get_logger()


class LogPrefix:
    """Prefixes for logging subprocess output."""

    RUN = "[RUN]"
    RUN_STDOUT = "[RUN STDOUT]"
    RUN_STDERR = "[RUN STDERR]"


def _log_command(command: str):
    """Write a command to the log with a special prefix."""
    # using extra={"markup": False} in case the command contains substrings
    # that would be interpreted as closing tags by the RichHandler
    logger.info(f"{LogPrefix.RUN} {command}", extra={"markup": False})


class CommandRunner(Protocol):
    """Protocol for functions that run commands, used for strategy injection."""

    def __call__(
        self,
        command_or_args: Sequence[str] | str,
        /,
        *,
        check: bool = True,
        quiet: bool = False,
        dry_run: bool = False,
    ) -> subprocess.Popen[str] | str:
        """Run a command in a subprocess, with logging and dry-run support."""
        ...


def run_command(
    command_or_args: Sequence[str] | str,
    /,
    *,
    check: bool = True,
    quiet: bool = False,
    dry_run: bool = False,
    **kwargs,
) -> subprocess.Popen[str] | str:
    """Run a command in a subprocess.

    The command's stdout and stderr outputs are streamed to the log
    line-by-line (with special prefixes) as the process runs.

    If in "dry run" mode, the command is not executed, and the function returns
    the command string. Otherwise, the :class:`subprocess.Popen` object is
    returned once the process has terminated.

    Parameters
    ----------
    command_or_args : Sequence[str] | str
        The command to run.
    check : bool, optional
        If True, raise an error if the process exits with a non-zero code,
        by default True.
    quiet : bool, optional
        If True, do not log the command, by default False.
    dry_run : bool, optional
        If True, do not execute the command, by default False.
    **kwargs
        Passed to :class:`subprocess.Popen`.

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

    def drain_process(process: subprocess.Popen[str]):
        """Read lines from the process's stdout and stderr and log them."""
        process_output(
            process.stdout,
            LogPrefix.RUN_STDOUT,
        )
        process_output(
            process.stderr,
            LogPrefix.RUN_STDERR,
            log_level=logging.ERROR,
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
        _log_command(command)

    if not dry_run:
        process: subprocess.Popen[str] = subprocess.Popen(
            command_or_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **kwargs,
        )

        while process.poll() is None:
            drain_process(process)

        # final drain: the poll() loop can exit before the last lines written
        # just prior to process termination are read, so flush any remaining
        # buffered output now that the process has exited.
        drain_process(process)

        if check and process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        run_output = process

    else:
        run_output = command

    return run_output
