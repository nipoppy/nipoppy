"""HPC runner service."""

from nipoppy.config.hpc import HpcConfig
from nipoppy.workflows.services.context import WorkflowContext


class HPCRunner:
    """
    Service for generating and submitting HPC jobs.

    Parameters
    ----------
    context : WorkflowContext
        The shared workflow context containing layout, logger, and config.
    hpc_config : HpcConfig
        The HPC-specific configuration.
    """

    def __init__(self, context: WorkflowContext, hpc_config: HpcConfig):
        self.context = context
        self.hpc_config = hpc_config

    def generate_script(self, job_params: dict) -> str:
        """
        Generate a submission script for the HPC scheduler.

        Parameters
        ----------
        job_params : dict
            The parameters for the job (e.g., command, resources).

        Returns
        -------
        str
            The generated submission script.
        """
        # Basic implementation for testing
        script = "#!/bin/bash\n"
        if hasattr(self.hpc_config, "account"):
            script += f"#SBATCH --account={self.hpc_config.account}\n"
        if "command" in job_params:
            script += f"\n{job_params['command']}\n"
        return script

    def submit(self, job_params: dict) -> str:
        """
        Submit a job to the HPC scheduler.

        Parameters
        ----------
        job_params : dict
            The parameters for the job (e.g., command, resources).

        Returns
        -------
        str
            The job ID returned by the scheduler.
        """
        # In a real implementation, this would write the script to a file
        # and call the scheduler (e.g., via pysqa or subprocess)
        script = self.generate_script(job_params)
        return self._submit_to_scheduler(script)

    def _submit_to_scheduler(self, script: str) -> str:
        """Submit a script to the scheduler.

        This is separated to allow easy mocking in tests.
        """
        # Placeholder for actual submission logic
        return "dummy_job_id"
