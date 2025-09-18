"""Abstract class for workflow runners and runner utilities."""

import json
import shlex
import subprocess
from abc import ABC
from pathlib import Path
from typing import Optional, Tuple

from boutiques import bosh

from nipoppy.config.boutiques import BoutiquesConfig
from nipoppy.config.container import ContainerConfig
from nipoppy.container import ContainerOptionsHandler, get_container_options_handler
from nipoppy.env import ContainerCommandEnum, StrOrPathLike
from nipoppy.utils.utils import TEMPLATE_REPLACE_PATTERN
from nipoppy.workflows.pipeline import BasePipelineWorkflow


class Runner(BasePipelineWorkflow, ABC):
    """Abstract class for workflow runners."""

    # TODO Generic type for pipeline config and pipeline step config attributes

    def __init__(
        self,
        simulate: bool = False,
        keep_workdir: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.simulate = simulate
        self.keep_workdir = keep_workdir

    def launch_boutiques_run(
        self,
        participant_id: str,
        session_id: str,
        container_handler: Optional[ContainerOptionsHandler] = None,
        objs: Optional[list] = None,
        **kwargs,
    ):
        """Launch a pipeline run using Boutiques."""
        bosh_exec_launch_args = []

        if self.verbose:
            bosh_exec_launch_args.append("--debug")

        # process the descriptor if it containers Nipoppy-specific placeholder
        # expressions (legacy behaviour)
        if TEMPLATE_REPLACE_PATTERN.search(self.descriptor["command-line"]):
            self.logger.info("Processing the JSON descriptor")
            descriptor_str = self.process_template_json(
                self.descriptor,
                participant_id=participant_id,
                session_id=session_id,
                objs=objs,
                **kwargs,
                return_str=True,
            )
        else:
            descriptor_str = json.dumps(self.descriptor)
            if (
                container_handler is None
                or self.descriptor.get("container-image") is None
            ):
                bosh_exec_launch_args.append("--no-container")
            else:
                bosh_exec_launch_args.extend(
                    [
                        "--no-automount",
                        "--container-opts",
                        shlex.join(container_handler.args),
                    ]
                )
                if container_handler.command in (
                    ContainerCommandEnum.SINGULARITY,
                    ContainerCommandEnum.APPTAINER,
                ):
                    bosh_exec_launch_args.extend(
                        [
                            "--imagepath",
                            str(self.fpath_container),
                            "--force-singularity",
                        ]
                    )
                elif container_handler.command == ContainerCommandEnum.DOCKER:
                    bosh_exec_launch_args.append("--force-docker")

        # validate the descriptor
        self.logger.debug(f"Descriptor string: {descriptor_str}")
        self.logger.info("Validating the JSON descriptor")
        bosh(["validate", descriptor_str])

        # process and validate the invocation
        self.logger.info("Processing the JSON invocation")
        invocation_str = self.process_template_json(
            self.invocation,
            participant_id=participant_id,
            session_id=session_id,
            objs=objs,
            **kwargs,
            return_str=True,
        )
        self.logger.debug(f"Invocation string: {invocation_str}")
        self.logger.info("Validating the JSON invocation")
        bosh(["invocation", "-i", invocation_str, descriptor_str])

        # run as a subprocess so that stdout/error are captured in the log
        # by default, this will raise an exception if the command fails
        if self.simulate:
            self.logger.info("Simulating pipeline command")
            try:
                self.run_command(
                    ["bosh", "exec", "simulate", "-i", invocation_str, descriptor_str],
                    quiet=True,
                )
                if bosh_exec_launch_args:
                    self.logger.info(
                        f"Additional launch options: {bosh_exec_launch_args}"
                    )
            except subprocess.CalledProcessError as exception:
                raise RuntimeError(
                    f"Pipeline simulation failed (return code: {exception.returncode})"
                )
        else:
            self.logger.info("Running pipeline command")
            try:
                self.run_command(
                    (
                        [
                            "bosh",
                            "exec",
                            "launch",
                            "--stream",
                            descriptor_str,
                            invocation_str,
                        ]
                        + bosh_exec_launch_args
                    ),
                    quiet=True,
                )
            except subprocess.CalledProcessError as exception:
                raise RuntimeError(
                    "Pipeline did not complete successfully"
                    f" (return code: {exception.returncode})"
                    ". Hint: make sure the shell command above is correct."
                )

        return descriptor_str, invocation_str

    def process_container_config(
        self,
        participant_id: str,
        session_id: str,
        bind_paths: Optional[list[StrOrPathLike]] = None,
    ) -> Tuple[str, ContainerOptionsHandler]:
        """Update container config and generate container command."""
        if bind_paths is None:
            bind_paths = []

        # always bind the dataset's root directory
        bind_paths = [self.layout.dpath_root] + bind_paths

        # get and process container config
        container_config = self.pipeline_step_config.get_container_config()
        container_config = ContainerConfig(
            **self.process_template_json(
                container_config.model_dump(),
                participant_id=participant_id,
                session_id=session_id,
            )
        )
        self.logger.debug(f"Initial container config: {container_config}")

        # get and process Boutiques config
        boutiques_config = BoutiquesConfig(
            **self.process_template_json(
                self.boutiques_config.model_dump(),
                participant_id=participant_id,
                session_id=session_id,
            )
        )

        # update container config with additional information from Boutiques config
        self.logger.debug(f"Boutiques config: {boutiques_config}")
        if boutiques_config != BoutiquesConfig():
            self.logger.debug("Updating container config with config from descriptor")
            container_config.merge(boutiques_config.get_container_config())

        container_handler = get_container_options_handler(
            container_config, logger=self.logger
        )

        # add bind paths
        for bind_path in bind_paths:
            if Path(bind_path).resolve() != Path.cwd().resolve():
                container_handler.add_bind_path(bind_path)

        self.logger.debug(f"Using container handler: {container_handler}")

        container_command = container_handler.prepare_container(
            subcommand=boutiques_config.CONTAINER_SUBCOMMAND,
        )

        return container_command, container_handler
