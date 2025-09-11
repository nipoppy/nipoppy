"""Abstract class for workflow runners and runner utilities."""

from abc import ABC

from nipoppy.workflows.pipeline import BasePipelineWorkflow


class Runner(BasePipelineWorkflow, ABC):
    """Abstract class for workflow runners."""

    # TODO Generic type for pipeline config and pipeline step config attributes

    # Function to implement:
    # TODO launch boutiques
    # TODO launch process container config
    ...
