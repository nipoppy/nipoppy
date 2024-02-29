"""Workflow for init command."""

from pathlib import Path

from nipoppy.utils import FPATH_SAMPLE_CONFIG, FPATH_SAMPLE_MANIFEST
from nipoppy.workflows.workflow import _Workflow


class InitWorkflow(_Workflow):
    """Workflow for init command."""

    def __init__(self, dpath_root: Path, **kwargs):
        """Initialize the workflow."""
        super().__init__(dpath_root=dpath_root, name="init", **kwargs)

    def run_main(self):
        """Create dataset directory structure."""
        # dataset must not already exist
        if self.dpath_root.exists():
            raise FileExistsError("Dataset directory already exists")

        # create directories
        for dpath in self.layout.dpaths:
            self.run_command(f"mkdir -p {dpath}")
        self.logger.info(f"Created an empty dataset at {self.dpath_root}")

        # copy sample config file
        self.run_command(f"cp {FPATH_SAMPLE_CONFIG} {self.layout.fpath_config}")

        # copy sample manifest file
        self.run_command(f"cp {FPATH_SAMPLE_MANIFEST} {self.layout.fpath_manifest}")

        # inform user to edit the sample files
        self.logger.warning(
            f"Sample config and manifest files copied to {self.layout.fpath_config}"
            f" and {self.layout.fpath_manifest} respectively. They should be edited"
            " to match your dataset"
        )
