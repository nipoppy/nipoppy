"""Container runner service."""

from nipoppy.workflows.services.context import WorkflowContext


class ContainerRunner:
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
        simulate: bool = False,
        bosh_exec_launch_args: list | None = None,
        run_command=None,
    ) -> int:
        """
        Execute the container with the given invocation string and descriptor string.

        Parameters
        ----------
        invocation_str : str
            The Boutiques invocation as a JSON string.
        descriptor_str : str
            The Boutiques descriptor as a JSON string.
        simulate : bool, optional
            Whether to simulate the execution instead of running it.
        bosh_exec_launch_args : list, optional
            Additional arguments for bosh exec launch.
        run_command : callable, optional
            A function to execute the command. Should act like subprocess.run
            or runner.run_command.

        Returns
        -------
        int
            The exit code of the container execution.
        """
        import subprocess

        from nipoppy.exceptions import ExecutionError
        from nipoppy.logger import get_logger

        logger = get_logger()

        if bosh_exec_launch_args is None:
            bosh_exec_launch_args = []

        if simulate:
            logger.info("Simulating pipeline command")
            command = ["bosh", "exec", "simulate", "-i", invocation_str, descriptor_str]
            try:
                if run_command:
                    run_command(command, quiet=True)
                else:
                    subprocess.run(command, check=True)
                if bosh_exec_launch_args:
                    logger.info(f"Additional launch options: {bosh_exec_launch_args}")
                return 0
            except subprocess.CalledProcessError as exception:
                raise ExecutionError(
                    f"Pipeline simulation failed (return code: {exception.returncode})"
                )
        else:
            logger.info("Running pipeline command")
            command = [
                "bosh",
                "exec",
                "launch",
                "--stream",
                descriptor_str,
                invocation_str,
            ] + bosh_exec_launch_args
            try:
                if run_command:
                    run_command(command, quiet=True)
                else:
                    subprocess.run(command, check=True)
                return 0
            except subprocess.CalledProcessError as exception:
                raise ExecutionError(
                    "Pipeline did not complete successfully"
                    f" (return code: {exception.returncode})"
                    ". Hint: make sure the shell command above is correct."
                )
