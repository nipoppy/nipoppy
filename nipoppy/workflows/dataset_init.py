"""Workflow for init command."""

import json
import logging
from pathlib import Path
from typing import Optional

import requests

from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    LogColor,
    StrOrPathLike,
)
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import (
    DPATH_DESCRIPTORS,
    DPATH_INVOCATIONS,
    DPATH_TRACKER_CONFIGS,
    FPATH_SAMPLE_CONFIG,
    FPATH_SAMPLE_MANIFEST,
    check_participant_id,
    check_session_id,
)
from nipoppy.workflows.base import BaseWorkflow


class InitWorkflow(BaseWorkflow):
    """Workflow for init command."""

    # do not validate since the dataset has not been created yet
    validate_layout = False

    def __init__(
        self,
        dpath_root: Path,
        use_dalatad=False,
        bids_source=None,
        fpath_layout: Optional[StrOrPathLike] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
    ):
        """Initialize the workflow."""
        super().__init__(
            dpath_root=dpath_root,
            name="init",
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )
        self.use_dalatad = use_dalatad
        self.fname_readme = "README.md"
        self.bids_source = bids_source

    def run_main(self):
        """Create dataset directory structure.

        Create directories and add a readme in each.
        Copy boutiques descriptors and invocations.
        Copy default config files.


        If the BIDS source dataset is requested, it is copied.
        If dataladd is used, it is installed with datalad.
        """
        # dataset must not already exist
        if self.dpath_root.exists():
            raise FileExistsError("Dataset directory already exists")

        self._init_as_datalad_dataset()

        # create directories
        for dpath in self.layout.dpaths:

            if dpath.stem != "bids" or self.bids_source is None:
                self.mkdir(dpath)
                continue

            if not self.use_dalatad:
                self.copytree(self.bids_source, str(dpath), log_level=logging.DEBUG)
                continue

            from datalad import api

            self.logger.info(
                f"Installing datalad BIDS raw dataset from {self.bids_source}."
            )
            dataset = None
            dataset = self.dpath_root

            api.install(
                dataset=dataset,
                path=dpath,
                source=self.bids_source,
                result_renderer="disabled",
            )

        self._write_readmes()

        # copy descriptor files
        for fpath_descriptor in DPATH_DESCRIPTORS.iterdir():
            self.copy(
                fpath_descriptor,
                self.layout.dpath_descriptors / fpath_descriptor.name,
                log_level=logging.DEBUG,
            )

        # copy sample invocation files
        for fpath_invocation in DPATH_INVOCATIONS.iterdir():
            self.copy(
                fpath_invocation,
                self.layout.dpath_invocations / fpath_invocation.name,
                log_level=logging.DEBUG,
            )

        # copy sample tracker config files
        for fpath_tracker_config in DPATH_TRACKER_CONFIGS.iterdir():
            self.copy(
                fpath_tracker_config,
                self.layout.dpath_tracker_configs / fpath_tracker_config.name,
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

        if self.use_dalatad:

            api.install(
                dataset=dataset,
                path=self.dpath_root / "code" / "templateflow",
                source="https://github.com/templateflow/templateflow.git",
                result_renderer="disabled",
            )

            # install repronim containers for easy access to bids apps
            # and update path to default mriqc and fmriprep images
            api.install(
                dataset=dataset,
                path=self.layout.dpath_containers / "repronim",
                source="///repronim/containers",
                result_renderer="disabled",
            )
            self._update_config()

            api.save(
                dataset=self.dpath_root,
                path=self.dpath_root / ".",
                message="Nipoppy layout initialized.",
            )

        # inform user to edit the sample files
        self.logger.warning(
            f"Sample config and manifest files copied to {self.layout.fpath_config}"
            f" and {self.layout.fpath_manifest} respectively. They should be edited"
            " to match your dataset"
        )

    def _init_as_datalad_dataset(self) -> None:
        if not self.use_dalatad:
            return None
        from datalad import api

        api.create(path=self.dpath_root, result_renderer="disabled")
        self._make_git_attributes()
        self._make_git_ignore()

    def _update_config(self) -> None:
        """Update global config to adapt it to using datalad."""
        with open(self.layout.fpath_config, "r") as f:
            content = json.load(f)

        content["SUBSTITUTIONS"][
            "[[NIPOPPY_DPATH_CONTAINERS]]"
        ] = "[[NIPOPPY_DPATH_ROOT]]/proc/containers"
        content["SUBSTITUTIONS"][
            "[[TEMPLATEFLOW_HOME]]"
        ] = "[[NIPOPPY_DPATH_ROOT]]/code/templateflow"

        for i, pipeline in enumerate(content["PROC_PIPELINES"]):
            if pipeline["NAME"] in ["mriqc", "fmriprep"]:
                content["PROC_PIPELINES"][i]["CONTAINER_INFO"]["FILE"] = (
                    "[[NIPOPPY_DPATH_CONTAINERS]]/repronim/images/bids/"
                    "bids-[[NIPOPPY_PIPELINE_NAME]]--"
                    "[[NIPOPPY_PIPELINE_VERSION]].sing"
                )
            elif pipeline["NAME"] == "heudiconv":
                content["PROC_PIPELINES"][i]["CONTAINER_INFO"]["FILE"] = (
                    "[[NIPOPPY_DPATH_CONTAINERS]]/repronim/images/nipy/"
                    "nipy-[[NIPOPPY_PIPELINE_NAME]]--"
                    "[[NIPOPPY_PIPELINE_VERSION]].sing"
                )
        with open(self.layout.fpath_config, "w") as f:
            json.dump(content, f, indent=4)

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
        participant_ids = sorted(
            [
                x.name
                for x in (self.layout.dpath_bids).iterdir()
                if x.is_dir() and x.name.startswith(BIDS_SUBJECT_PREFIX)
            ]
        )

        self.logger.info("Creating a manifest file from the BIDS dataset content.")

        for ppt in participant_ids:

            session_ids = sorted(
                [
                    x.name
                    for x in (self.layout.dpath_bids / ppt).iterdir()
                    if x.is_dir() and x.name.startswith(BIDS_SESSION_PREFIX)
                ]
            )
            if not session_ids:
                self.logger.warning(
                    f"Skipping subject '{ppt}': could not find a session level folder."
                )
                continue

            for ses in session_ids:
                datatypes = sorted(
                    [
                        x.name
                        for x in (self.layout.dpath_bids / ppt / ses).iterdir()
                        if x.is_dir()
                    ]
                )

                df[Manifest.col_participant_id].append(check_participant_id(ppt))
                df[Manifest.col_session_id].append(check_session_id(ses))
                df[Manifest.col_datatype].append(datatypes)

        df[Manifest.col_visit_id] = df[Manifest.col_session_id]

        manifest = Manifest(df).validate()
        self.save_tabular_file(manifest, self.layout.fpath_manifest)

    def _make_git_attributes(self) -> None:
        CONTENT = [
            "* annex.backend=MD5E",
            "**/.git* annex.largefiles=nothing",
            "*.csv annex.largefiles=nothing",
            "*.tsv annex.largefiles=nothing",
            "*.json annex.largefiles=nothing",
            "**/README.md annex.largefiles=nothing",
        ]
        with open(self.dpath_root / ".gitattributes", "w") as f:
            for line in CONTENT:
                f.write(f"{line}\n")

    def _make_git_ignore(self) -> None:
        CONTENT = ["sourcedata", "scratch", "proc/pybids/bids_db"]
        with open(self.dpath_root / ".gitignore", "w") as f:
            for line in CONTENT:
                f.write(f"{line}\n")

    def run_cleanup(self):
        """Log a success message."""
        self.logger.info(
            f"[{LogColor.SUCCESS}]Successfully initialized a dataset "
            f"at {self.dpath_root}![/]"
        )
        return super().run_cleanup()
