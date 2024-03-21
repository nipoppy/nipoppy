"""PipelineRunner workflow."""

import logging
from pathlib import Path
from typing import Optional

from boutiques import bosh

from nipoppy.config.boutiques import BoutiquesConfig
from nipoppy.config.singularity import prepare_singularity
from nipoppy.workflows.pipeline import BasePipelineWorkflow


class PipelineRunner(BasePipelineWorkflow):
    """Pipeline runner."""

    def __init__(
        self,
        dpath_root: Path | str,
        pipeline_name: str,
        pipeline_version: str,
        participant=None,
        session=None,
        simulate=False,
        logger: Optional[logging.Logger] = None,
        dry_run=False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            name="run",
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            participant=participant,
            session=session,
            logger=logger,
            dry_run=dry_run,
        )
        self.simulate = simulate
        self.dpaths_to_check.extend(
            [self.dpath_pipeline_output, self.dpath_pipeline_work]
        )

    def process_singularity_config(
        self,
        participant: str,
        session: str,
        bind_paths: Optional[list[str | Path]] = None,
    ) -> str:
        """Update Singularity config and generate Singularity command."""
        if bind_paths is None:
            bind_paths = []

        # get singularity config
        singularity_config = self.pipeline_config.get_singularity_config()
        self.logger.debug(f"Initial Singularity config: {singularity_config}")

        # update singularity config with additional information from Boutiques config
        boutiques_config = self.get_boutiques_config(participant, session)
        self.logger.debug(f"Boutiques config: {boutiques_config}")
        if boutiques_config != BoutiquesConfig():
            self.logger.info("Updating Singularity config with config from descriptor")
            singularity_config.merge_args_and_env_vars(
                boutiques_config.get_singularity_config()
            )

        # add bind paths
        for bind_path in bind_paths:
            singularity_config.add_bind_path(bind_path)

        self.logger.info(f"Using Singularity config: {singularity_config}")

        singularity_command = prepare_singularity(
            singularity_config, check=True, logger=self.logger
        )

        return singularity_command

    def launch_boutiques_run(
        self, participant: str, session: str, objs: Optional[list] = None, **kwargs
    ):
        """Launch a pipeline run using Boutiques."""
        # process and validate the descriptor
        self.logger.info("Processing the JSON descriptor")
        descriptor_str = self.process_template_json(
            self.descriptor,
            participant=participant,
            session=session,
            objs=objs,
            **kwargs,
            return_str=True,
        )
        self.logger.debug(f"Descriptor string: {descriptor_str}")
        self.logger.info("Validating the JSON descriptor")
        bosh(["validate", descriptor_str])

        # process and validate the invocation
        self.logger.info("Processing the JSON invocation")
        invocation_str = self.process_template_json(
            self.invocation,
            participant=participant,
            session=session,
            objs=objs,
            **kwargs,
            return_str=True,
        )
        self.logger.debug(f"Invocation string: {invocation_str}")
        self.logger.info("Validating the JSON invocation")
        bosh(["invocation", "-i", invocation_str, descriptor_str])

        # run as a subprocess so that stdout/error are captured in the log
        if self.simulate:
            self.run_command(
                ["bosh", "exec", "simulate", "-i", invocation_str, descriptor_str]
            )
        else:
            self.run_command(
                ["bosh", "exec", "launch", "--stream", descriptor_str, invocation_str]
            )

        return descriptor_str, invocation_str

    def run_single(self, participant: str, session: str):
        """Run pipeline on a single participant/session."""
        # set up PyBIDS database
        self.set_up_bids_db(
            dpath_bids_db=self.dpath_pipeline_bids_db,
            participant=participant,
            session=session,
        )

        # get singularity command
        singularity_command = self.process_singularity_config(
            participant=participant,
            session=session,
            bind_paths=[
                self.layout.dpath_bids,
                self.dpath_pipeline_output,
                self.dpath_pipeline_work,
                self.dpath_pipeline_bids_db,
            ],
        )

        self.launch_boutiques_run(
            participant, session, singularity_command=singularity_command
        )

    def run_cleanup(self, **kwargs):
        """Run pipeline runner cleanup."""
        if self.dpath_pipeline_bids_db.exists():
            self.run_command(["rm", "-rf", self.dpath_pipeline_bids_db])
        return super().run_cleanup(**kwargs)
