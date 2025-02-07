"""Workflow for init command."""

import logging
from pathlib import Path
from typing import Optional

import requests

from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    FAKE_SESSION_ID,
    LogColor,
    StrOrPathLike,
)
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import (
    DPATH_SAMPLE_PIPELINES,
    FPATH_SAMPLE_CONFIG,
    FPATH_SAMPLE_MANIFEST,
    check_participant_id,
    check_session_id,
    session_id_to_bids_session_id,
)
from nipoppy.workflows.base import BaseWorkflow


class InitWorkflow(BaseWorkflow):
    """Workflow for init command."""

    # do not validate since the dataset has not been created yet
    validate_layout = False

    def __init__(
        self,
        dpath_root: Path,
        bids_source=None,
        mode="symlink",
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="init",
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logging=True,
        )
        self.fname_readme = "README.md"
        self.bids_source = bids_source
        self.mode = mode

    def run_main(self):
        """Create dataset directory structure.

        Create directories and add a readme in each.
        Copy boutiques descriptors and invocations.
        Copy default config files.

        If the BIDS source dataset is requested, it is symlinked.
        """
        # dataset must not already exist
        if self.dpath_root.exists():
            try:
                filenames = [
                    f for f in self.dpath_root.iterdir() if f.name != ".DS_STORE"
                ]

            except NotADirectoryError:
                raise FileExistsError(f"Dataset is an existing file: {self.dpath_root}")

            if len(filenames) > 0:
                raise FileExistsError(
                    f"Dataset directory is non-empty: {self.dpath_root}"
                )

        # create directories
        for dpath in self.layout.dpaths:
            # If a bids_source is passed it means datalad is installed.
            if self.bids_source is not None and dpath.stem == "bids":
                if self.mode == "copy":
                    self.copytree(self.bids_source, str(dpath), log_level=logging.DEBUG)
                elif self.mode == "move":
                    self.movetree(self.bids_source, str(dpath), log_level=logging.DEBUG)
                elif self.mode == "symlink":
                    self.mkdir(self.dpath_root)
                    self.create_symlink(
                        self.bids_source, str(dpath), log_level=logging.DEBUG
                    )
                else:
                    raise ValueError(f"Invalid mode: {self.mode}")
            else:
                self.mkdir(dpath)

        self._write_readmes()

        # copy pipeline files
        for dpath_pipeline in DPATH_SAMPLE_PIPELINES.iterdir():
            self.copytree(
                dpath_pipeline,
                self.layout.dpath_pipelines / dpath_pipeline.name,
                log_level=logging.DEBUG,
            )

        # copy sample config and manifest files
        self.copy(
            FPATH_SAMPLE_CONFIG, self.layout.fpath_config, log_level=logging.DEBUG
        )

        if self.bids_source is not None:
            self._init_manifest_from_bids_dataset()
        else:
            self.copy(
                FPATH_SAMPLE_MANIFEST,
                self.layout.fpath_manifest,
                log_level=logging.DEBUG,
            )

        # inform user to edit the sample files
        self.logger.warning(
            f"Sample config and manifest files copied to {self.layout.fpath_config}"
            f" and {self.layout.fpath_manifest} respectively. They should be edited"
            " to match your dataset"
        )

    def _write_readmes(self) -> None:
        if self.dry_run:
            return None
        for dpath, description in self.layout.dpath_descriptions:
            fpath_readme = dpath / self.fname_readme
            if description is None:
                continue
            if dpath.stem != "bids" or self.bids_source is None:
                fpath_readme.write_text(f"{description}\n")
            elif self.bids_source is not None and not fpath_readme.exists():
                gh_org = "bids-standard"
                gh_repo = "bids-starter-kit"
                commit = "f2328c58238bdf2088bc587b0eb4198131d8ffe2"
                path = "templates/README.MD"
                url = (
                    "https://raw.githubusercontent.com/"
                    f"{gh_org}/{gh_repo}/{commit}/{path}"
                )
                response = requests.get(url)
                fpath_readme.write_text(response.content.decode("utf-8"))

    def _init_manifest_from_bids_dataset(self) -> None:
        """Assume a BIDS dataset with session level folders.

        No BIDS validation is done.
        """
        if self.dry_run:
            return None
        df = {
            Manifest.col_participant_id: [],
            Manifest.col_visit_id: [],
            Manifest.col_session_id: [],
            Manifest.col_datatype: [],
        }
        bids_participant_ids = sorted(
            [
                x.name
                for x in (self.layout.dpath_bids).iterdir()
                if x.is_dir() and x.name.startswith(BIDS_SUBJECT_PREFIX)
            ]
        )

        self.logger.info("Creating a manifest file from the BIDS dataset content.")

        for bids_participant_id in bids_participant_ids:
            bids_session_ids = sorted(
                [
                    x.name
                    for x in (self.layout.dpath_bids / bids_participant_id).iterdir()
                    if x.is_dir() and x.name.startswith(BIDS_SESSION_PREFIX)
                ]
            )
            if len(bids_session_ids) == 0:
                # if there are no session folders
                # we will add a fake session for this participant
                self.logger.warning(
                    "Could not find session-level folder(s) for participant "
                    f"{bids_participant_id}, using session {FAKE_SESSION_ID} "
                    "in the manifest"
                )
                bids_session_ids = [f"{session_id_to_bids_session_id(FAKE_SESSION_ID)}"]

            for bids_session_id in bids_session_ids:
                if (
                    bids_session_id
                    == f"{session_id_to_bids_session_id(FAKE_SESSION_ID)}"
                ):
                    # if the session is fake, we don't expect BIDS data
                    # to have session dir in the path
                    datatypes = sorted(
                        [
                            x.name
                            for x in (
                                self.layout.dpath_bids / bids_participant_id
                            ).iterdir()
                            if x.is_dir()
                        ]
                    )
                else:
                    datatypes = sorted(
                        [
                            x.name
                            for x in (
                                self.layout.dpath_bids
                                / bids_participant_id
                                / bids_session_id
                            ).iterdir()
                            if x.is_dir()
                        ]
                    )

                df[Manifest.col_participant_id].append(
                    check_participant_id(bids_participant_id)
                )
                df[Manifest.col_session_id].append(check_session_id(bids_session_id))
                df[Manifest.col_datatype].append(datatypes)

        df[Manifest.col_visit_id] = df[Manifest.col_session_id]

        manifest = Manifest(df).validate()
        self.save_tabular_file(manifest, self.layout.fpath_manifest)

    def run_cleanup(self):
        """Log a success message."""
        self.logger.info(
            f"[{LogColor.SUCCESS}]Successfully initialized a dataset "
            f"at {self.dpath_root}![/]"
        )
        return super().run_cleanup()
