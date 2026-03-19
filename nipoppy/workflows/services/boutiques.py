"""Boutiques runner service."""

from __future__ import annotations

import subprocess
from typing import Protocol, Sequence

from nipoppy.exceptions import ExecutionError
from nipoppy.logger import get_logger

logger = get_logger()


class CommandRunner(Protocol):
    """Protocol for functions that run commands, used for dependency injection."""

    def __call__(
        self,
        command_or_args: Sequence[str] | str,
        /,
        *,
        check: bool,
        quiet: bool,
        dry_run: bool,
    ) -> subprocess.Popen[str] | str:
        # flake8: noqa
        # flake8: qa
        # We disable the flake8 to prevent it from complaining about missing DocString.
        ...


class CommandBuilder(Protocol):
    def __call__(
        self,
        invocation: str,
        descriptor: str,
        args: list[str],
    ) -> list[str]: ...


class ErrorBuilder(Protocol):
    def __call__(self, exit_code: int) -> str: ...


def _run_command(
    command: list[str],
    run_command: CommandRunner | None,
    dry_run: bool,
) -> None:
    """Run or delegate the command."""
    if run_command:
        run_command(command, quiet=True, dry_run=dry_run)
    elif dry_run:
        logger.info("Dry run enabled, skipping command execution")
    else:
        subprocess.run(command, check=True)


def _run_bosh_command(
    invocation_str: str,
    descriptor_str: str,
    bosh_exec_launch_args: list[str] | None = None,
    run_command: CommandRunner | None = None,
    dry_run: bool = False,
    *,
    mode: str,
    command_builder: CommandBuilder,
    error_message_builder: ErrorBuilder,
) -> int:
    """Execute a Boutiques command with shared error handling.

    Parameters
    ----------
    command_builder : CommandBuilder
        A function that builds the command to run based on the invocation, descriptor, and additional args. Returns a list of command arguments.
    error_message_builder : ErrorBuilder
        A function that builds an error message based on the exit code of a failed command.
    """
    if bosh_exec_launch_args is None:
        bosh_exec_launch_args = []

    command = command_builder(
        invocation_str,
        descriptor_str,
        bosh_exec_launch_args,
    )
    logger.info(f"{mode} pipeline command")

    try:
        _run_command(command, run_command, dry_run)
    except subprocess.CalledProcessError as exception:
        raise ExecutionError(error_message_builder(exception.returncode))

    return 0


def run_bosh_launch(
    invocation_str: str,
    descriptor_str: str,
    bosh_exec_launch_args: list[str] | None = None,
    run_command: CommandRunner | None = None,
    dry_run: bool = False,
) -> int:
    """Execute a Boutiques launch command.

    Parameters
    ----------
    invocation_str : str
        The Boutiques invocation as a JSON string.
    descriptor_str : str
        The Boutiques descriptor as a JSON string.
    bosh_exec_launch_args : list of str, optional
        Additional arguments for ``bosh exec launch``.
    run_command : CommandRunner, optional
        A function to execute the command. Should act like ``subprocess.run``
        or ``runner.run_command``.
    dry_run : bool, optional
        If True, build and log the command but skip actual execution.

    Returns
    -------
    int
        The exit code of the container execution.
    """

    def command_builder(invocation: str, descriptor: str, args: list[str]) -> list[str]:
        return [
            "bosh",
            "exec",
            "launch",
            "--stream",
            descriptor,
            invocation,
        ] + args

    def error_message_builder(exit_code: int) -> str:
        return (
            f"Pipeline execution failed (return code: {exit_code})."
            "Hint: make sure the shell command above is correct."
        )

    return _run_bosh_command(
        invocation_str=invocation_str,
        descriptor_str=descriptor_str,
        bosh_exec_launch_args=bosh_exec_launch_args,
        run_command=run_command,
        dry_run=dry_run,
        mode="Running",
        command_builder=command_builder,
        error_message_builder=error_message_builder,
    )


def run_bosh_simulate(
    invocation_str: str,
    descriptor_str: str,
    bosh_exec_launch_args: list[str] | None = None,
    run_command: CommandRunner | None = None,
    dry_run: bool = False,
) -> int:
    """Execute a Boutiques simulate command."""

    def command_builder(invocation: str, descriptor: str, args: list[str]) -> list[str]:
        return [
            "bosh",
            "exec",
            "simulate",
            "-i",
            invocation,
            descriptor,
        ]

    def error_message_builder(exit_code: int) -> str:
        return f"Pipeline simulation failed (return code: {exit_code})"

    logger.info(f"Additional launch options: {bosh_exec_launch_args}")
    rv = _run_bosh_command(
        invocation_str=invocation_str,
        descriptor_str=descriptor_str,
        bosh_exec_launch_args=bosh_exec_launch_args,
        run_command=run_command,
        dry_run=dry_run,
        mode="Simulating",
        command_builder=command_builder,
        error_message_builder=error_message_builder,
    )
    return rv
