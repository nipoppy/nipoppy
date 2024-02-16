"""Workflow for init command."""

from pathlib import Path

from nipoppy.utils import FPATH_SAMPLE_CONFIG, FPATH_SAMPLE_MANIFEST
from nipoppy.workflows.workflow import _Workflow


class DatasetInitWorkflow(_Workflow):
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
        self.logger.info(
            f"Sample configuration file copied to: {self.layout.fpath_config}"
            " (should be customized for the specific dataset)"
        )

        # copy sample manifest file
        self.run_command(f"cp {FPATH_SAMPLE_MANIFEST} {self.layout.fpath_manifest}")
        self.logger.info(
            f"Sample manifest file copied to: {self.layout.fpath_config}"
            " (should be customized for the specific dataset)"
        )
