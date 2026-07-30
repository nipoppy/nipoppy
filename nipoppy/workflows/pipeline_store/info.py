"""Workflow for the pipeline info command."""

from pathlib import Path
from typing import Optional

from packaging.version import Version

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PipelineTypeEnum, StrOrPathLike
from nipoppy.exceptions import WorkflowError
from nipoppy.layout import DatasetLayout
from nipoppy.logger import emphasize, get_logger
from nipoppy.pipeline_validation import _load_pipeline_config_file
from nipoppy.workflows.base import BaseDatasetWorkflow

logger = get_logger()


class PipelineInfoWorkflow(BaseDatasetWorkflow):
    """Show details about a pipeline installed in a dataset."""

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version

        super().__init__(
            dpath_root,
            name="pipeline_info",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logfile=True,
        )

    def _find_pipeline(
        self,
    ) -> tuple[Path, PipelineTypeEnum, BasePipelineConfig]:
        """Find the requested pipeline bundle and load its configuration."""
        matches = []
        installed = []

        for pipeline_type in PipelineTypeEnum:
            dpath_store = self.study.layout.get_dpath_pipeline_store(pipeline_type)
            for fpath_config in sorted(
                dpath_store.glob(f"*/{DatasetLayout.fname_pipeline_config}")
            ):
                config = _load_pipeline_config_file(fpath_config)
                installed.append(f"{config.NAME} {config.VERSION}")

                if config.NAME != self.pipeline_name:
                    continue
                if (
                    self.pipeline_version is not None
                    and config.VERSION != self.pipeline_version
                ):
                    continue

                matches.append((fpath_config.parent, pipeline_type, config))

        if len(matches) == 0:
            requested = self.pipeline_name
            if self.pipeline_version is not None:
                requested += f" {self.pipeline_version}"
            available = ", ".join(installed) or "none"
            raise WorkflowError(
                f"No installed pipeline found for {requested}. "
                f"Installed pipelines: {available}"
            )

        if self.pipeline_version is None:
            latest_version = max(Version(match[2].VERSION) for match in matches)
            matches = [
                match
                for match in matches
                if Version(match[2].VERSION) == latest_version
            ]

        if len(matches) > 1:
            locations = ", ".join(str(match[0]) for match in matches)
            raise WorkflowError(
                f"Multiple installed bundles match {self.pipeline_name}"
                f" {matches[0][2].VERSION}: {locations}"
            )

        return matches[0]

    def _log_step(self, dpath_bundle: Path, index: int, step) -> None:
        """Log details about a pipeline step."""
        logger.info(emphasize(f"Step {index}: {step.NAME}"))
        logger.info(f"\tAnalysis level: {step.ANALYSIS_LEVEL.value}")

        for label, field in (
            ("Descriptor", "DESCRIPTOR_FILE"),
            ("Invocation", "INVOCATION_FILE"),
            ("HPC config", "HPC_CONFIG_FILE"),
            ("Tracker config", "TRACKER_CONFIG_FILE"),
            ("PyBIDS ignore file", "PYBIDS_IGNORE_FILE"),
        ):
            if (relative_path := getattr(step, field, None)) is not None:
                logger.info(f"\t{label}: {dpath_bundle / relative_path}")

    def run_main(self):
        """Show details about the requested pipeline."""
        dpath_bundle, pipeline_type, config = self._find_pipeline()

        logger.info(emphasize(f"{config.NAME} {config.VERSION}"))
        logger.info(f"Bundle: {dpath_bundle}")
        logger.info(f"Type: {pipeline_type.value}")
        logger.info(f"Description: {config.DESCRIPTION or 'None'}")
        logger.info(f"Steps: {len(config.STEPS)}")

        for index, step in enumerate(config.STEPS, start=1):
            self._log_step(dpath_bundle, index, step)
