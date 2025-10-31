"""Workflow for pipeline search command."""

from typing import Optional

import pandas as pd
from rich import box
from rich.table import Table

from nipoppy.console import _INDENT, CONSOLE_STDOUT
from nipoppy.env import LogColor
from nipoppy.utils.html import strip_html_tags
from nipoppy.workflows.base import BaseWorkflow
from nipoppy.zenodo_api import ZenodoAPI

CONSOLE_WIDTH = CONSOLE_STDOUT.size.width
MAX_CONSOLE_WIDTH = min(CONSOLE_WIDTH, 120 - _INDENT)


class PipelineSearchWorkflow(BaseWorkflow):
    """Search Zenodo for existing pipeline configurations and print results table."""

    _api_search_size = int(1e9)
    col_zenodo_id = "Zenodo ID"
    col_title = "Title"
    col_description = "Description"
    col_downloads = "Downloads"

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
            description = hit.get("metadata", {}).get("description")
            if description is not None:
                description = strip_html_tags(description).strip()
            zenodo_id_with_link = f"[link={hit.get('doi_url')}]{hit.get('id')}[/link]"
            data_for_df.append(
                {
                    self.col_zenodo_id: zenodo_id_with_link,
                    self.col_title: hit.get("title"),
                    self.col_description: description,
                    self.col_downloads: hit.get("stats", {}).get("downloads"),
                }
            )
        return (
            pd.DataFrame(data_for_df)
            .sort_values(self.col_downloads, ascending=False)
            .iloc[: self.size]
        )

    def _df_to_table(self, df_hits: pd.DataFrame) -> Table:
        width = {
            "zenodo_id": len(self.col_zenodo_id),
            "downloads": len(self.col_downloads),
            "title": 20,
        }

        width["description"] = min(
            MAX_CONSOLE_WIDTH, MAX_CONSOLE_WIDTH - sum(width.values(), 10)
        )

        table = Table(box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column(self.col_zenodo_id, justify="center", width=width["zenodo_id"])
        table.add_column(self.col_title, justify="left", min_width=width["title"])

        print(width)
        if CONSOLE_WIDTH > 80:
            table.add_column(
                self.col_description,
                justify="left",
                max_width=width["description"],
                no_wrap=True,  # Required to make overflow="ellipsis" work
                overflow="ellipsis",
            )
        table.add_column(self.col_downloads, justify="right", width=width["downloads"])
        cols = [col.header for col in table.columns]

        for _, row in df_hits[cols].iterrows():
            table.add_row(*[str(cell) for cell in row])
        return table

    def run_main(self):
        """Run the workflow."""
        with CONSOLE_STDOUT.status("Searching Nipoppy pipelines on Zenodo..."):
            # we get all results and sort/slice them ourselves since we cannot currently
            # sort by "mostdownloaded" through the API
            results = self.zenodo_api.search_records(
                query=self.query,
                keywords=["Nipoppy"],
                size=self._api_search_size,
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

        n_shown = min(len(hits), self.size)
        message = f"Showing {n_shown} of {n_total} results"
        if n_shown < n_total:
            message += " (use --size to show more)"
        self.logger.info(message)
        CONSOLE_STDOUT.print(table)
