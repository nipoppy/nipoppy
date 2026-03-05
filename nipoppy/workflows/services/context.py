"""Workflow context data class."""

from dataclasses import dataclass

from nipoppy.config.main import Config
from nipoppy.layout import DatasetLayout
from nipoppy.logger import NipoppyLogger


@dataclass
class WorkflowContext:
    """
    Encapsulates shared state passed between workflow components.

    Parameters
    ----------
    layout : DatasetLayout
        The BIDS dataset layout.
    logger : NipoppyLogger
        The structured logger instance.
    config : Config
        The global configuration object.
    """

    layout: DatasetLayout
    logger: NipoppyLogger
    config: Config
