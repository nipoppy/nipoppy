"""Workflow for pipeline info command."""

from nipoppy.logger import emphasize, get_logger
from nipoppy.workflows.pipeline import BasePipelineWorkflow

logger = get_logger()


class PipelineInfoWorkflow(BasePipelineWorkflow):
    """Show configuration details for a pipeline installed in a study."""

    def __init__(
        self,
        dpath_root,
        pipeline_name,
        pipeline_version=None,
        fpath_layout=None,
        verbose=False,
        dry_run=False,
    ):
        super().__init__(
            dpath_root,
            name="pipeline_info",
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logfile=True,
        )

    def run_setup(self):
        """Find the pipeline type, then run the usual pipeline setup."""
        # self._pipeline_type defaults to PROCESSING always !
        for pipeline_type, pipelines in self.study._get_pipeline_info_map().items():
            if self.pipeline_name in pipelines:
                self._pipeline_type = pipeline_type
                break
        super().run_setup()

    def run_main(self):
        """Show configuration details for a pipeline."""
        logger.info(
            emphasize(
                f"{self.pipeline_config.NAME} {self.pipeline_config.VERSION}"
                f" ({self.pipeline_config.PIPELINE_TYPE.value})"
            )
        )
        fname_config = self.study.layout.fname_pipeline_config
        logger.info(f"Config: {self.dpath_pipeline_bundle / fname_config}")
        for step in self.pipeline_config.STEPS:
            logger.info(f"Step: {step.NAME}")
            for label, field in (
                ("Descriptor", "DESCRIPTOR_FILE"),
                ("Invocation", "INVOCATION_FILE"),
                ("HPC config", "HPC_CONFIG_FILE"),
                ("Tracker config", "TRACKER_CONFIG_FILE"),
                ("PyBIDS ignore", "PYBIDS_IGNORE_FILE"),
            ):
                fpath = getattr(step, field, None)
                if fpath is not None:
                    logger.info(f"- {label}: {self.dpath_pipeline_bundle / fpath}")

    def get_participants_sessions_to_run(self, participant_id, session_id):
        """Not used."""
        raise NotImplementedError(
            "Pipeline info command has no participant and session loop"
        )

    def run_single(self, participant_id, session_id):
        """Not used."""
        raise NotImplementedError(
            "Pipeline info command has no participant and session loop"
        )
