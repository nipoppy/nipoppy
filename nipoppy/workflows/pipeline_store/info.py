"""Workflow for pipeline info command."""

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PROGRAM_NAME
from nipoppy.exceptions import WorkflowError
from nipoppy.logger import emphasize, get_logger
from nipoppy.utils.utils import load_json
from nipoppy.workflows.base import BaseDatasetWorkflow
from nipoppy.workflows.pipeline import get_pipeline_version

logger = get_logger()


class PipelineInfoWorkflow(BaseDatasetWorkflow):
    """Show the file paths of a pipeline that has been installed into a dataset."""

    def __init__(
        self,
        dpath_root,
        pipeline_name,
        pipeline_version=None,
        fpath_layout=None,
        verbose=False,
        dry_run=False,
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

    def run_main(self):
        """Show the bundle and Boutiques file paths of a pipeline."""
        # find which pipeline type the pipeline is installed as
        pipeline_type_to_info_map = self.study._get_pipeline_info_map()
        pipeline_type = None
        for pipeline_type_to_check, pipelines in pipeline_type_to_info_map.items():
            if self.pipeline_name in pipelines:
                pipeline_type = pipeline_type_to_check
                installed_versions = pipelines[self.pipeline_name]
                break

        if pipeline_type is None:
            raise WorkflowError(
                f"Pipeline {self.pipeline_name} is not installed. Installed pipelines"
                f' can be listed with the "{PROGRAM_NAME} pipeline list" command'
            )

        if self.pipeline_version is None:
            self.pipeline_version = get_pipeline_version(
                pipeline_name=self.pipeline_name,
                dpath_pipelines=self.study.layout.get_dpath_pipeline_store(
                    pipeline_type
                ),
            )
        elif self.pipeline_version not in installed_versions:
            raise WorkflowError(
                f"Version {self.pipeline_version} of pipeline {self.pipeline_name} is"
                " not installed. Installed versions: " + ", ".join(installed_versions)
            )

        dpath_bundle = self.study.layout.get_dpath_pipeline_bundle(
            pipeline_type, self.pipeline_name, self.pipeline_version
        )
        pipeline_config = BasePipelineConfig(
            **load_json(
                dpath_bundle / self.study.layout.fname_pipeline_config,
                allow_json5=True,
            )
        )

        logger.info(
            emphasize(
                f"{pipeline_config.NAME} {pipeline_config.VERSION}"
                f" ({pipeline_type.value})"
            )
        )
        logger.info(f"Bundle: {dpath_bundle}")
        for step in pipeline_config.STEPS:
            logger.info(f"Step: {step.NAME}")
            if step.DESCRIPTOR_FILE is not None:
                logger.info(f"\t- Descriptor: {dpath_bundle / step.DESCRIPTOR_FILE}")
            if step.INVOCATION_FILE is not None:
                logger.info(f"\t- Invocation: {dpath_bundle / step.INVOCATION_FILE}")
