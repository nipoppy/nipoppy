"""Workflow for mincify command."""

import logging
from functools import cached_property
import json
import os
from pathlib import Path
from typing import Optional

from boutiques import bosh

from nipoppy.config.pipeline import BidsPipelineConfig
from nipoppy.utils import get_pipeline_tag, process_template_str
from nipoppy.workflows.runner import PipelineRunner

# Example command:
# nipoppy mincify --dataset-root /data/chamal/projects/danmat/pepp/data/imaging_data/raw/nipoppy/dep/ --pipeline nii2mnc --pipeline-version 1.9.18 --participant-id 5002 --session-id 1 --data-types anat

class MincConversionRunner(PipelineRunner):
    """Convert data to MINC."""

    def __init__(
        self,
        dpath_root: Path | str,
        pipeline_name: str,
        pipeline_version: str,
        participant_id: str = None,
        session_id: str = None,
        simulate: bool = False,
        data_types: list = [],
        fpath_layout: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
    ):
        super().__init__(
            dpath_root=dpath_root,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            participant_id=participant_id,
            session_id=session_id,
            simulate=simulate,
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.data_types=data_types
        self.name = "minc_conversion"
        self.dpaths_to_check = []  # do not create any pipeline-specific directory

    @cached_property
    def pipeline_config(self) -> BidsPipelineConfig:
        """Get the user config for the MINC conversion software."""
        return self.config.get_pipeline_config(
            self.pipeline_name,
            self.pipeline_version
        )

    def get_fpath_descriptor_builtin(self) -> Path:
        """Get the path to the built-in descriptor file."""
        fname_descriptor_builtin = get_pipeline_tag(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version
        )

        return super().get_fpath_descriptor_builtin(
            fname=f"{fname_descriptor_builtin}.json"
        )
    

    def get_participants_session_ids_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """Return bidsified participant_id-session_id pairs to run the pipeline on."""
        return self.doughnut.get_bidsified_participants_session_ids(
            participant_id=participant_id, session_id=session_id
        )

    def get_files_to_mincify(
        self, participant_id: str, session_id: str, data_types: list,
    ) -> list[Path]:
        """
        Get single files to mincify for a single participant_id and session_id
        (since nii2mnc takes one file at a time).

        """
        participant_dir = "sub-" + participant_id
        session_dir = "ses-" + session_id

        # crawl through directory tree and get all file paths
        in_dirs = [self.layout.dpath_bids / participant_dir / session_dir / dtype for dtype in data_types]

        in_files = []
        out_files = []
        
        for in_dir in in_dirs:
            fnames = sorted(os.listdir(in_dir))
            in_files.extend(f'{str(in_dir)}/{fname}' for fname in fnames if fname.endswith("nii.gz"))

            # out dir has the same directory structure as in dir, but under DATASET_ROOT/minc instead of DATASET_ROOT/bids
            out_dir = str(in_dir).replace(str(self.layout.dpath_bids), str(self.layout.dpath_minc))
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            # same file name, just with .mnc extension instead of .nii.gz
            out_files.extend(f'{str(out_dir)}/{fname.replace("nii.gz", "mnc")}' for fname in fnames if fname.endswith("nii.gz"))
        
        in_out_files = list(zip(in_files, out_files))

        return in_out_files
    
    def process_minc_template_json(
        self,
        template_json: dict,
        objs: Optional[list] = None,
        return_str: bool = False,
        **kwargs,
    ):
        """Replace template strings in a JSON object."""
        if objs is None:
            objs = []
        objs.extend([self, self.layout])

        self.logger.debug("Available replacement strings: ")
        max_len = max(len(k) for k in kwargs)
        for k, v in kwargs.items():
            self.logger.debug(f"\t{k}:".ljust(max_len + 3) + v)
        self.logger.debug(f"\t+ all attributes in: {objs}")

        template_json_str = process_template_str(
            json.dumps(template_json),
            objs=objs,
            **kwargs,
        )

        return template_json_str if return_str else json.loads(template_json_str)
    
    def launch_minc_boutiques_run(
        self, in_file: str, out_file: str, objs: Optional[list] = None, **kwargs
    ):
        """Launch a pipeline run using Boutiques."""

        # process and validate the descriptor
        self.logger.info("Processing the JSON descriptor")
        descriptor_str = self.process_minc_template_json(
            self.descriptor,
            objs=objs,
            **kwargs,
            return_str=True,
        )
        self.logger.debug(f"Descriptor string: {descriptor_str}")
        self.logger.info("Validating the JSON descriptor")
        bosh(["validate", descriptor_str])

        # process and validate the invocation
        self.logger.info("Processing the JSON invocation")

        self.invocation['in_file'] = in_file
        self.invocation['out_file'] = out_file

        invocation_str = self.process_minc_template_json(
            self.invocation,
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

    def run_single(self, participant_id: str, session_id: str):
        """Run MINC conversion on a single bidsified participant_id/session_id."""
        # Returns a list of tuples. First item in each tuple is an input .nii.gz file to be mincified, second item is an output .mnc file        
        fpaths = self.get_files_to_mincify(
            participant_id, session_id, self.data_types
        )

        # get container command
        container_command = self.process_container_config(
            participant_id=participant_id,
            session_id=session_id,
            bind_paths=[
                self.layout.dpath_bids,
                self.layout.dpath_minc
            ],
        )

        try:
            for in_file, out_file in fpaths:
                # run pipeline with Boutiques
                self.launch_minc_boutiques_run(
                    in_file, out_file, container_command=container_command
                )

            # update status
            self.doughnut.set_status(
                participant_id=participant_id,
                session_id=session_id,
                col=self.doughnut.col_in_minc,
                status=True,
            )
        
        except Exception as exception:
            self.logger.error(
                "Error running nii2mnc"
                f" for participant_id {participant_id} session_id {session_id}: {exception}"
            )

    def run_cleanup(self, **kwargs):
        """
        Clean up after main MINC conversion part is run.

        Specifically:
        - Write updated doughnut file
        """
        # To do - why does this break?
        # update_doughnut = self.pipeline_config.get_update_doughnut(
        #     step_name=self.pipeline_step
        # )
        # if update_doughnut and not self.simulate:
        #     self.save_tabular_file(self.doughnut, self.layout.fpath_doughnut)
        self.save_tabular_file(self.doughnut, self.layout.fpath_doughnut)
        return super().run_cleanup(**kwargs)

    def generate_fpath_log(
        self,
        dname_parent: Optional[str | list[str]] = None,
        fname_stem: Optional[str] = None,
    ) -> Path:
        """Generate a log file path."""
        if dname_parent is None:
            dname_parent = get_pipeline_tag(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version
            )
        return super().generate_fpath_log(dname_parent, fname_stem)
