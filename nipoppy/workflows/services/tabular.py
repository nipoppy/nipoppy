"""Tabular data handler service."""

import pandas as pd

from nipoppy.workflows.services.context import WorkflowContext


class TabularDataHandler:
    """
    Service for reading, writing, and validating tabular data files.

    Parameters
    ----------
    context : WorkflowContext
        The shared workflow context.
    """

    def __init__(self, context: WorkflowContext):
        self.context = context

    def load(self, file_path: str) -> pd.DataFrame:
        """
        Load and validate a tabular data file.

        Parameters
        ----------
        file_path : str
            The path to the tabular file.

        Returns
        -------
        pd.DataFrame
            The loaded data.
        """
        # Basic implementation for testing
        # In a real implementation, this would include validation logic
        # based on the expected schema for the file type
        return pd.read_csv(file_path)

    def save(self, df: pd.DataFrame, file_path: str) -> None:
        """
        Save a DataFrame to a tabular file.

        Parameters
        ----------
        df : pd.DataFrame
            The data to save.
        file_path : str
            The path to save the file to.
        """
        # Basic implementation for testing
        df.to_csv(file_path, index=False)
