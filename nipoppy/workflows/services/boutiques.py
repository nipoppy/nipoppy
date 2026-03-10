"""Container runner service."""

from __future__ import annotations

import subprocess
from collections.abc import Callable

from nipoppy.exceptions import ExecutionError
from nipoppy.logger import get_logger
from nipoppy.workflows.services.context import WorkflowContext

logger = get_logger()


class BoshRunner:
    """
    Service for executing containerized applications via Boutiques.

    Parameters
    ----------
    context : WorkflowContext
        The shared workflow context.
    descriptor : dict
        The Boutiques descriptor for the container.
    """

    def __init__(self, context: WorkflowContext, descriptor: dict):
        self.context = context
        self.descriptor = descriptor

    def run(
        self,
        invocation_str: str,
        descriptor_str: str,
        bosh_exec_launch_args: list[str] | None = None,
        run_command: Callable | None = None,
        dry_run: bool = False,
    ) -> int:
        """Execute the container with the given invocation string and descriptor string.

        Parameters
        ----------
        invocation_str : str
            The Boutiques invocation as a JSON string.
        descriptor_str : str
            The Boutiques descriptor as a JSON string.
        bosh_exec_launch_args : list of str, optional
            Additional arguments for ``bosh exec launch``.
        run_command : Callable, optional
            A function to execute the command. Should act like ``subprocess.run``
            or ``runner.run_command``.
        dry_run : bool, optional
            If True, build and log the command but skip actual execution.
            Simulation of the pipeline itself is controlled by using
            :class:`BoshSimulate` instead of :class:`BoshRunner`.

        Returns
        -------
        int
            The exit code of the container execution.
        """
        if bosh_exec_launch_args is None:
            bosh_exec_launch_args = []

        command = self._build_command(
            invocation_str,
            descriptor_str,
            bosh_exec_launch_args=bosh_exec_launch_args,
        )
        logger.info(f"{self.mode} pipeline command")

        try:
            self._execute(command, run_command, dry_run)
        except subprocess.CalledProcessError as exception:
            error_message = self._get_error_message(exit_code=exception.returncode)
            raise ExecutionError(
                f"{error_message} (return code: {exception.returncode})"
            )

        if self.mode == "Simulating" and bosh_exec_launch_args:
            logger.info(f"Additional launch options: {bosh_exec_launch_args}")

        return 0

    @property
    def mode(self) -> str:
        """Return the execution mode."""
        return "Running"

    def _build_command(
        self,
        invocation_str: str,
        descriptor_str: str,
        *,
        bosh_exec_launch_args: list[str],
    ) -> list[str]:
        """Build the bosh command to execute."""
        return [
            "bosh",
            "exec",
            "launch",
            "--stream",
            descriptor_str,
            invocation_str,
        ] + bosh_exec_launch_args

    def _execute(
        self,
        command: list[str],
        run_command: subprocess.run | None,
        dry_run: bool,
    ) -> None:
        """Execute or delegate the command."""
        if run_command:
            run_command(command, quiet=True, dry_run=dry_run)
        elif dry_run:
            logger.info("Dry run enabled, skipping command execution")
        else:
            subprocess.run(command, check=True)

    def _get_error_message(self, exit_code: int) -> str:
        """Return the appropriate error message."""
        return (
            f"Pipeline did not complete successfully (return code: {exit_code})."
            "Hint: make sure the shell command above is correct."
        )


class BoshSimulate(BoshRunner):
    """Service for simulating container execution via Boutiques."""

    @property
    def mode(self) -> str:
        """Return the execution mode."""
        return "Simulating"

    def _build_command(
        self,
        invocation_str: str,
        descriptor_str: str,
        *,
        bosh_exec_launch_args: list[str],
    ) -> list[str]:
        """Build the bosh command to execute."""
        return ["bosh", "exec", "simulate", "-i", invocation_str, descriptor_str]

    def _get_error_message(self, exit_code: int) -> str:
        """Return the appropriate error message."""
        return f"Pipeline simulation failed (return code: {exit_code})"
