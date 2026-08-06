"""Workflow for pipeline list command."""

from nipoppy.env import PROGRAM_NAME, PipelineTypeEnum
from nipoppy.logger import emphasize, get_logger
from nipoppy.workflows.base import BaseDatasetWorkflow

logger = get_logger()


class PipelineListWorkflow(BaseDatasetWorkflow):
    """List pipelines and versions that have been installed into a dataset."""

    def __init__(
        self,
        dpath_root,
        fpath_layout=None,
        verbose=False,
        dry_run=False,
    ):
        super().__init__(
            dpath_root,
            name="pipeline_list",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logfile=True,
        )

    def _log_pipeline_info(
        self,
        pipeline_type: PipelineTypeEnum,
        pipelines: dict[str, list[str]],
    ):
        if len(pipelines) == 0:
            logger.warning(f"No available {pipeline_type.value} pipelines")
            return

        logger.info(
            emphasize(f"Available {pipeline_type.value} pipelines and versions")
        )

        # to align the pipeline version substrings
        max_characters = max(len(pipeline_name) for pipeline_name in pipelines.keys())

        for pipeline_name, pipeline_versions in pipelines.items():
            logger.info(
                f"\t- {pipeline_name.ljust(max_characters)}"
                f" ({', '.join(pipeline_versions)})"
            )

    def run_main(self):
        """List the available pipelines in a dataset."""
        pipeline_type_to_info_map = self.study._get_pipeline_info_map()

        logger.info(
            f"Checking pipelines installed in {self.study.layout.dpath_pipelines}"
        )
        for pipeline_type, pipelines in pipeline_type_to_info_map.items():
            self._log_pipeline_info(pipeline_type, pipelines)

        logger.info(
            f'Pipelines can be installed with the "{PROGRAM_NAME} pipeline install"'
            " command"
        )
