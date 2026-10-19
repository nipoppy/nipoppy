"""Workflow for pipeline info command."""

from nipoppy.env import PROGRAM_NAME
from nipoppy.exceptions import WorkflowError
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

    def run_main(self):
        """Show configuration details for a pipeline."""
        pipeline_type_to_info_map = self.study._get_pipeline_info_map()
        self._pipeline_type = None
        for pipeline_type_to_check, pipelines in pipeline_type_to_info_map.items():
            if self.pipeline_name in pipelines:
                self._pipeline_type = pipeline_type_to_check
                installed_versions = pipelines[self.pipeline_name]
                break

        if self._pipeline_type is None:
            raise WorkflowError(
                f"Pipeline {self.pipeline_name} is not installed. Installed pipelines"
                f' can be listed with the "{PROGRAM_NAME} pipeline list" command'
            )

        if self.pipeline_version is None:
            self.check_pipeline_version()
        elif self.pipeline_version not in installed_versions:
            raise WorkflowError(
                f"Version {self.pipeline_version} of pipeline {self.pipeline_name} is"
                " not installed. Installed versions: " + ", ".join(installed_versions)
            )

        logger.info(
            emphasize(
                f"{self.pipeline_config.NAME} {self.pipeline_config.VERSION}"
                f" ({self._pipeline_type.value})"
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
        """Not used: this workflow does not loop over participants."""
        raise NotImplementedError(
            "Pipeline info command has no participant and session loop"
        )

    def run_single(self, participant_id, session_id):
        """Not used: this workflow does not loop over participants."""
        raise NotImplementedError(
            "Pipeline info command has no participant and session loop"
        )
