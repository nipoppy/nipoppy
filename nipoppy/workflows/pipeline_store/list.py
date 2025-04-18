"""Workflow for pipeline list command."""

from collections import defaultdict

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PROGRAM_NAME, LogColor, PipelineTypeEnum
from nipoppy.layout import DatasetLayout
from nipoppy.utils import load_json
from nipoppy.workflows.base import BaseDatasetWorkflow


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

    def _get_pipeline_info_map(
        self,
    ) -> dict[PipelineTypeEnum, dict[str, list[str]]]:
        pipeline_type_to_info_map = {}
        for pipeline_type in PipelineTypeEnum:
            pipeline_names_to_versions_map = defaultdict(list)
            dpath_pipeline_bundles = (
                self.layout.dpath_pipelines
                / DatasetLayout.pipeline_type_to_dname_map[pipeline_type]
            )
            for fpath_config in sorted(
                dpath_pipeline_bundles.glob(f"*/{self.layout.fname_pipeline_config}")
            ):
                try:
                    pipeline_config = BasePipelineConfig(**load_json(fpath_config))
                except Exception as exception:
                    raise RuntimeError(
                        f"Error when loading pipeline config at {fpath_config}"
                        f": {exception}"
                    )

                pipeline_names_to_versions_map[pipeline_config.NAME].append(
                    pipeline_config.VERSION
                )

            pipeline_type_to_info_map[pipeline_type] = pipeline_names_to_versions_map

        return pipeline_type_to_info_map

    def _log_pipeline_info(
        self,
        pipeline_type: PipelineTypeEnum,
        pipelines: dict[str, list[str]],
    ):
        if len(pipelines) == 0:
            self.logger.info(
                f"[{LogColor.FAILURE}]No available {pipeline_type.value} "
                "pipelines[/]"
            )
            return

        self.logger.info(
            f"[{LogColor.SUCCESS}]Available {pipeline_type.value} pipelines and "
            "versions:[/]"
        )

        # to align the pipeline version substrings
        max_characters = max(len(pipeline_name) for pipeline_name in pipelines.keys())

        for pipeline_name, pipeline_versions in pipelines.items():
            self.logger.info(
                f"\t- {pipeline_name.ljust(max_characters)}"
                f" ({', '.join(pipeline_versions)})"
            )

    def run_main(self):
        """List the available pipelines in a dataset."""
        pipeline_type_to_info_map = self._get_pipeline_info_map()

        self.logger.info(
            f"Checking pipelines installed in {self.layout.dpath_pipelines}"
        )
        for pipeline_type, pipelines in pipeline_type_to_info_map.items():
            self._log_pipeline_info(pipeline_type, pipelines)

        self.logger.info(
            f'Pipelines can be installed with the "{PROGRAM_NAME} pipeline install"'
            " command"
        )
