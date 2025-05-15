"""Workflow for pipeline validate command."""

from pathlib import Path
from typing import Optional

import boutiques as bosh

from nipoppy.env import LogColor
from nipoppy.workflows.base import BaseWorkflow


class PipelineCreateWorkflow(BaseWorkflow):
    """Workflow for pipeline validate command."""

    def __init__(
        self,
        target: Path,
        source_descriptor: Optional[Path] = None,
        verbose=False,
        dry_run=False,
    ):
        super().__init__(
            name="pipeline_create",
            verbose=verbose,
            dry_run=dry_run,
        )
        self.target = target
        self.source_descriptor = source_descriptor

    def run_main(self):
        """Run the main workflow."""
        self.logger.debug(f"Creating pipeline bundle at {self.target}")
        create_bundle(target=self.target, source_descriptor=self.source_descriptor)
        self.logger.info(
            f"[{LogColor.SUCCESS}]Pipeline bundle successfully created at "
            f"{self.target}![/]",
        )


def create_bundle(target: Path, source_descriptor: Optional[Path] = None):
    """Create a pipeline bundle."""
    if target.exists():
        raise IsADirectoryError(
            f"Target directory {target} already exists. "
            "Please remove it or choose a different name.",
        )
    bosh.create(target.as_posix())

    raise NotImplementedError()
