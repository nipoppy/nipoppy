"""PipelineTracker workflow."""

from nipoppy.workflows.pipeline import BasePipelineWorkflow


class PipelineTracker(BasePipelineWorkflow):
    """Pipeline tracker."""

    def run_setup(self, **kwargs):
        """Load/initialize the bagel file."""
        # TODO
        return super().run_setup(**kwargs)

    def run_single(self, participant: str, session: str):
        """Run tracker on a single participant/session."""
        # get list of paths

        # check status and add to bagel file

        # TODO handle potentially zipped archives

        pass

    def run_cleanup(self, **kwargs):
        """Save the bagel file."""
        return super().run_cleanup(**kwargs)
