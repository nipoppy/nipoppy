"""Workflow for init command."""

from pathlib import Path
from typing import Optional

try:
    from nipoppy._version import __version__
except ImportError:
    __version__ = "unknown"
from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    FAKE_SESSION_ID,
    NIPOPPY_DIR_NAME,
    PipelineTypeEnum,
    StrOrPathLike,
)
from nipoppy.exceptions import FileOperationError
from nipoppy.logger import get_logger
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import fileops
from nipoppy.utils.bids import (
    check_participant_id,
    check_session_id,
    session_id_to_bids_session_id,
)
from nipoppy.utils.utils import (
    DPATH_HPC,
    FPATH_SAMPLE_BIDS_DATASET_DESCRIPTION,
    FPATH_SAMPLE_BIDSIGNORE,
    FPATH_SAMPLE_CONFIG,
    FPATH_SAMPLE_MANIFEST,
    process_template_str,
)
from nipoppy.workflows.base import BaseDatasetWorkflow

logger = get_logger()


def copy_template(
    path_source: Path,
    path_dest: Path,
    *,
    dry_run: bool = False,
    **template_kwargs,
):
    """Copy a file with template substitution.

    Parameters
    ----------
    path_source
        Source template file path
    path_dest
        Destination file path
    **template_kwargs
        Keyword arguments passed to process_template_str for substitution
    """
    logger.debug(f"Copying template {path_source} to {path_dest}")
    if not dry_run:
        with open(path_source, "r") as f:
            content = process_template_str(f.read(), **template_kwargs)
        fileops.mkdir(Path(path_dest).parent, dry_run=dry_run)
        with open(path_dest, "w") as f:
            f.write(content)


class InitWorkflow(BaseDatasetWorkflow):
    """Workflow for init command."""

    def __init__(
        self,
        dpath_root: Path,
        bids_source=None,
        mode="symlink",
        force=False,
        container_store: StrOrPathLike | None = None,
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
            _skip_logfile=True,
            _validate_layout=False,
        )
        self.fname_readme = "README.md"
        self.bids_source = bids_source
        self.mode = mode
        self.force = force
        self.container_store = container_store

    def run_main(self):
        """Create dataset directory structure.

        Create directories and add a readme in each.
        Copy boutiques descriptors and invocations.
        Copy default config files.
        Copy HPC config files.
        """
        self._raise_on_invalid_existing_root_dir()

        # create directories
        fileops.mkdir(self.dpath_root / NIPOPPY_DIR_NAME, dry_run=self.dry_run)
        for dpath in self.study.layout.get_paths(directory=True, include_optional=True):
            if self.bids_source is not None and dpath == self.study.layout.dpath_bids:
                self._handle_bids_source()
            elif (
                self.container_store is not None
                and dpath == self.study.layout.dpath_containers
            ):
                fileops.symlink(
                    self.container_store, dpath, force=self.force, dry_run=self.dry_run
                )
            else:
                fileops.mkdir(dpath, dry_run=self.dry_run)
                self._write_readme(
                    dpath, self.study.layout._dpath_descriptions.get(str(dpath))
                )

        # create empty pipeline config subdirectories
        for pipeline_type in PipelineTypeEnum:
            fileops.mkdir(
                self.study.layout.get_dpath_pipeline_store(pipeline_type),
                dry_run=self.dry_run,
            )

        # copy sample config and manifest files
        fileops.copy(
            FPATH_SAMPLE_CONFIG,
            self.study.layout.fpath_config,
            exist_ok=True,
            dry_run=self.dry_run,
        )

        if self.bids_source is not None:
            self._init_manifest_from_bids_dataset()
        else:
            fileops.copy(
                FPATH_SAMPLE_MANIFEST,
                self.study.layout.fpath_manifest,
                exist_ok=True,
                dry_run=self.dry_run,
            )

        # copy dataset description file if specified in layout
        if getattr(self.study.layout, "fpath_bids_dataset_description", None):
            copy_template(
                FPATH_SAMPLE_BIDS_DATASET_DESCRIPTION,
                self.study.layout.fpath_bids_dataset_description,
                version=__version__,
                dry_run=self.dry_run,
            )

        # copy bidsignore file if specified in layout
        if getattr(self.study.layout, "fpath_bidsignore", None):
            fileops.copy(
                FPATH_SAMPLE_BIDSIGNORE,
                self.study.layout.fpath_bidsignore,
            )

        # copy HPC files
        fileops.copy(
            DPATH_HPC,
            self.study.layout.dpath_hpc,
            exist_ok=True,
            dry_run=self.dry_run,
        )

        # inform user to edit the sample files
        logger.warning(
            "Sample config and manifest files copied to "
            f"{self.study.layout.fpath_config} and {self.study.layout.fpath_manifest} "
            "respectively. They should be edited to match your dataset"
        )

    def _raise_on_invalid_existing_root_dir(self) -> None:
        if not self.dpath_root.exists():
            return
        try:
            filenames = [f for f in self.dpath_root.iterdir() if f.name != ".DS_STORE"]
        except NotADirectoryError:
            raise FileOperationError(
                f"Study root path is an existing file: {self.dpath_root}"
            )

        if len(filenames) > 0:
            msg = f"Study root directory is non-empty: {self.dpath_root}"
            if self.force:
                logger.warning(f"{msg} `--force` specified, proceeding anyway.")
            else:
                raise FileOperationError(
                    f"{msg}. If this is intended, consider using the --force flag."
                )

    def _handle_bids_source(self) -> None:
        """Create bids source directory.

        Handles copy/move/symlink modes.
        If --force, attempt to remove the pre-existing conflicting bids source.
        """
        dpath = self.study.layout.dpath_bids

        # Handle edge case where we need to clobber existing data
        if dpath.exists() and self.force:
            fileops.rm(dpath, dry_run=self.dry_run)

        fileops.mkdir(dpath.parent, dry_run=self.dry_run)

        if self.mode == "copy":
            fileops.copy(self.bids_source, dpath, dry_run=self.dry_run)
        elif self.mode == "move":
            fileops.movetree(self.bids_source, dpath, dry_run=self.dry_run)
        elif self.mode == "symlink":
            fileops.symlink(self.bids_source, dpath, dry_run=self.dry_run)
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def _write_readme(self, dpath, description) -> None:
        if self.dry_run or description is None:
            return

        fpath_readme = dpath / self.fname_readme
        fpath_readme.write_text(f"{description}\n")

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
                for x in (self.study.layout.dpath_bids).iterdir()
                if x.is_dir() and x.name.startswith(BIDS_SUBJECT_PREFIX)
            ]
        )

        logger.info("Creating a manifest file from the BIDS dataset content.")

        for bids_participant_id in bids_participant_ids:
            bids_session_ids = sorted(
                [
                    x.name
                    for x in (
                        self.study.layout.dpath_bids / bids_participant_id
                    ).iterdir()
                    if x.is_dir() and x.name.startswith(BIDS_SESSION_PREFIX)
                ]
            )
            if len(bids_session_ids) == 0:
                # if there are no session folders
                # we will add a fake session for this participant
                logger.warning(
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
                                self.study.layout.dpath_bids / bids_participant_id
                            ).iterdir()
                            if x.is_dir()
                        ]
                    )
                else:
                    datatypes = sorted(
                        [
                            x.name
                            for x in (
                                self.study.layout.dpath_bids
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
        manifest.save_with_backup(
            self.study.layout.fpath_manifest, dry_run=self.dry_run
        )

    def run_cleanup(self):
        """Log a success message."""
        logger.success(f"Successfully initialized a dataset at {self.dpath_root}!")
        return super().run_cleanup()
