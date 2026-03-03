"""Container runner service."""

import json

from boutiques import bosh

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

    def run(self, invocation: dict) -> int:
        """
        Execute the container with the given invocation.

        Parameters
        ----------
        invocation : dict
            The Boutiques invocation parameters.

        Returns
        -------
        int
            The exit code of the container execution.
        """
        # Basic implementation for testing
        # In a real implementation, this would use the Boutiques API
        # to execute the container with the given descriptor and invocation
        descriptor_str = json.dumps(self.descriptor)
        invocation_str = json.dumps(invocation)

        # Validate descriptor and invocation
        bosh(["validate", descriptor_str])
        bosh(["invocation", "-i", invocation_str, descriptor_str])

        # Execute the container
        # Note: bosh() returns a list of results or a single result depending on the command  # noqa: E501
        # For 'exec launch', it returns an object with an exit_code attribute
        result = bosh(
            [
                "exec",
                "launch",
                "-i",
                invocation_str,
                descriptor_str,
            ]
        )

        # Handle the result which might be a list or a single object
        if isinstance(result, list) and len(result) > 0:
            return getattr(result[0], "exit_code", 0)
        return getattr(result, "exit_code", 0)
