"""Workflow for pipeline search command."""

from typing import Optional

import pandas as pd
from rich import box
from rich.table import Table

from nipoppy.console import CONSOLE_STDOUT
from nipoppy.env import LogColor
from nipoppy.workflows.base import BaseWorkflow
from nipoppy.zenodo_api import ZenodoAPI


class PipelineSearchWorkflow(BaseWorkflow):
    """Search Zenodo for existing pipeline configurations and print results table."""

    def __init__(
        self,
        query: str,
        zenodo_api: Optional[ZenodoAPI] = None,
        size: int = 10,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            name="pipeline_search",
            verbose=verbose,
            dry_run=dry_run,
        )
        self.zenodo_api = zenodo_api or ZenodoAPI()
        self.query = query
        self.size = size

        self.zenodo_api.set_logger(self.logger)

    def _hits_to_df(self, hits: list[dict]) -> pd.DataFrame:
        data_for_df = []
        for hit in hits:
            data_for_df.append(
                {
                    "Zenodo ID": hit.get("id"),
                    "Title": hit.get("title"),
                    "Description": hit.get("metadata", {}).get("description"),
                    "Downloads": hit.get("stats", {}).get("downloads"),
                }
            )
        return pd.DataFrame(data_for_df).sort_values("Downloads", ascending=False)

    def _df_to_table(self, df_hits: pd.DataFrame) -> Table:
        table = Table(box=box.MINIMAL_DOUBLE_HEAD)
        for column in df_hits.columns:
            table.add_column(column, justify="center")
        for _, row in df_hits.iterrows():
            table.add_row(*[str(cell) for cell in row])
        return table

    def run_main(self):
        """Run the workflow."""
        with CONSOLE_STDOUT.status("Searching Nipoppy pipelines on Zenodo..."):
            results = self.zenodo_api.search_records(
                query=self.query,
                keywords=["Nipoppy"],
                size=self.size,
            )
        hits = results["hits"]
        n_total = results["total"]

        if n_total == 0:
            self.logger.warning(
                f'[{LogColor.FAILURE}]No results found for query "{self.query}".[/red]'
            )
            return

        df_hits = self._hits_to_df(hits)
        table = self._df_to_table(df_hits)

        self.logger.info(f"Showing {len(hits)} of {n_total} results")
        CONSOLE_STDOUT.print(table)
