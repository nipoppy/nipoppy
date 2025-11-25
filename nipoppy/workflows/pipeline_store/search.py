"""Workflow for pipeline search command."""

from typing import Optional

import pandas as pd
from rich import box
from rich.table import Table

from nipoppy.console import _INDENT, CONSOLE_STDOUT
from nipoppy.env import ZENODO_COMMUNITY_ID
from nipoppy.logger import get_logger
from nipoppy.utils.html import strip_html_tags
from nipoppy.workflows.base import BaseWorkflow
from nipoppy.zenodo_api import ZenodoAPI

CURRENT_CONSOLE_WIDTH = CONSOLE_STDOUT.size.width
RESIZED_CONSOLE_WIDTH = min(CURRENT_CONSOLE_WIDTH, 120 - _INDENT)
MINIMIZED_TABLE_MAX_WIDTH = 80

logger = get_logger()


class PipelineSearchWorkflow(BaseWorkflow):
    """Search Zenodo for existing pipeline configurations and print results table."""

    _api_search_size = 100  # Page size cannot be greater than 100.
    col_zenodo_id = "Zenodo ID"
    col_title = "Title"
    col_description = "Description"
    col_downloads = "Downloads"
    widths = {
        col_zenodo_id: len(col_zenodo_id),
        col_downloads: len(col_downloads),
        col_title: 20,
    }
    # Add 10 extra spaces for padding and table borders
    widths[col_description] = min(
        RESIZED_CONSOLE_WIDTH, RESIZED_CONSOLE_WIDTH - sum(widths.values(), 10)
    )

    def __init__(
        self,
        query: str,
        zenodo_api: Optional[ZenodoAPI] = None,
        community: bool = False,
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
        self.zenodo_api.logger = logger  # use nipoppy logger configuration
        self.query = query
        self.community = community
        self.size = size

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
        table = Table(box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column(
            self.col_zenodo_id, justify="center", width=self.widths[self.col_zenodo_id]
        )
        table.add_column(
            self.col_title, justify="left", min_width=self.widths[self.col_title]
        )

        if CURRENT_CONSOLE_WIDTH > MINIMIZED_TABLE_MAX_WIDTH:
            table.add_column(
                self.col_description,
                justify="left",
                max_width=self.widths[self.col_description],
                no_wrap=True,  # Required to make overflow="ellipsis" work
                overflow="ellipsis",
            )
        table.add_column(
            self.col_downloads, justify="right", width=self.widths[self.col_downloads]
        )
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
                community_id=ZENODO_COMMUNITY_ID if self.community else None,
                keywords=["Nipoppy"],
                size=self._api_search_size,
            )

        hits = results["hits"]
        n_total = results["total"]

        if n_total == 0:
            logger.warning(f'No results found for query "{self.query}".')
            return

        df_hits = self._hits_to_df(hits)
        table = self._df_to_table(df_hits)

        n_shown = min(len(hits), self.size)
        message = f"Showing {n_shown} of {n_total} results"
        if n_shown < n_total:
            message += " (use --size to show more)"
        if not self.community:
            message += " (use --community to restrict to Nipoppy community)"
        logger.info(message)
        CONSOLE_STDOUT.print(table)
