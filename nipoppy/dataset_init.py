"""Workflow for init command."""
from pathlib import Path

from nipoppy.workflow import _Workflow


class DatasetInitWorkflow(_Workflow):
    """Workflow for init command."""

    def __init__(self, dpath_root: Path, **kwargs):
        """Initialize the workflow."""
        super().__init__(dpath_root=dpath_root, name="init", **kwargs)

    def run_main(self):
        """Create dataset directory structure."""
        if self.dpath_root.exists():
            raise FileExistsError("Dataset directory already exists")
        for dpath in self.layout.dpaths:
            self.run_command(f"mkdir -p {dpath}")
