"""Dataset layout."""

from functools import cached_property
from pathlib import Path
from typing import Any, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from nipoppy.base import Base
from nipoppy.env import NIPOPPY_DIR_NAME, PipelineTypeEnum, StrOrPathLike
from nipoppy.utils import FPATH_DEFAULT_LAYOUT, get_pipeline_tag, load_json


class PathInfo(BaseModel):
    """Relative path and description for a directory or file."""

    _is_directory: bool
    _is_required: bool = True

    path: Path = Field(description="Relative path to the file or directory")
    description: Optional[str] = Field(
        default=None,
        description="Description of the function of the file or directory",
    )


class DpathInfo(PathInfo):
    """Relative path and description for a directory."""

    _is_directory = True


class OptionalDpathInfo(DpathInfo):
    """Relative path and description for a directory that is optional."""

    _is_required = False


class FpathInfo(PathInfo):
    """Relative path and description for a file."""

    _is_directory = False


class OptionalFpathInfo(FpathInfo):
    """Relative path and description for a file that is optional."""

    _is_required = False


class LayoutConfig(BaseModel):
    """Relative paths for the dataset layout."""

    model_config = ConfigDict(extra="forbid")
    dpath_bids: DpathInfo = Field(description="Directory for raw imaging data in BIDS")
    dpath_derivatives: DpathInfo = Field(
        description="Directory for imaging derivatives"
    )
    dpath_sourcedata: DpathInfo = Field(
        description="Directory for source imaging and tabular data"
    )
    dpath_src_tabular: DpathInfo = Field(
        description=(
            "Directory for tabular data source files"
            " (e.g., downloaded CSVs, Excel files, RedCAP reports)"
        )
    )
    dpath_src_imaging: DpathInfo = Field(
        description="Directory for non-BIDS imaging data files and archives"
    )
    dpath_downloads: DpathInfo = Field(description="Directory for downloaded data")
    dpath_pre_reorg: DpathInfo = Field(
        description="Directory for unorganized source imaging files"
    )
    dpath_post_reorg: DpathInfo = Field(
        description="Directory for imaging data that is organized but not yet in BIDS"
    )
    dpath_code: DpathInfo = Field(description="Directory for code and scripts")
    dpath_hpc: OptionalDpathInfo = Field(
        description="Directory for HPC job submission template files"
    )
    dpath_pipelines: DpathInfo = Field(
        description=(
            "Directory for configurations or other files needed to run pipelines"
        )
    )
    dpath_containers: DpathInfo = Field(
        description="Directory for storing container images"
    )
    dpath_scratch: DpathInfo = Field(description="Directory for temporary files")
    dpath_pybids_db: DpathInfo = Field(description=("Directory for PyBIDS databases"))
    dpath_work: DpathInfo = Field(
        description=(
            "Directory for temporary/working files generated during pipeline runs"
        )
    )
    dpath_logs: DpathInfo = Field(description="Directory for logs generated by Nipoppy")
    dpath_tabular: DpathInfo = Field(description="Directory for tabular data")
    dpath_assessments: DpathInfo = Field(
        description="Directory for tabular assessment data"
    )

    fpath_config: FpathInfo = Field(description="Path to the configuration file")
    fpath_manifest: FpathInfo = Field(description="Path to the manifest file")
    fpath_curation_status: OptionalFpathInfo = Field(
        description=(
            "Path to the curation status file (for tracking the BIDSification process)"
        )
    )
    fpath_processing_status: OptionalFpathInfo = Field(
        description=(
            "Path to the processing status file (for tracking imaging derivative "
            "availability at the participant level)"
        )
    )
    fpath_demographics: OptionalFpathInfo = Field(
        description="Path to the study's demographics data file"
    )

    @cached_property
    def path_labels(self) -> list[str]:
        """Return a list of all path labels defined in the layout."""
        return list(self.model_dump().keys())

    @cached_property
    def path_infos(self) -> list[PathInfo]:
        """Return a list of all PathInfo objects defined in the layout."""
        return [getattr(self, path_label) for path_label in self.path_labels]

    def get_path_info(self, path_label: str) -> PathInfo:
        """Return the PathInfo object associated with the given path label."""
        return getattr(self, path_label)


class DatasetLayout(Base):
    """File/directory structure for a specific dataset."""

    # pipeline derivative subdirectories
    dname_pipeline_output = "output"
    dname_pipeline_idp = "idp"

    # pipeline store subdirectories
    pipeline_type_to_dname_map = {
        PipelineTypeEnum.BIDSIFICATION: "bidsification",
        PipelineTypeEnum.PROCESSING: "processing",
        PipelineTypeEnum.EXTRACTION: "extraction",
    }

    # file names
    fname_pipeline_config = "config.json"

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        fpath_config: Optional[StrOrPathLike] = None,
    ):
        """Initialize the object.

        Parameters
        ----------
        dpath_root : nipoppy.env.StrOrPathLike
            Path to the root directory of the dataset.
        fpath_config : Optional[nipoppy.env.StrOrPathLike], optional
            Path to the layout config to use, by default None.
            If None, the default layout will be used.

        Raises
        ------
        FileNotFoundError
            If ``fpath_config`` does not exist.
        """
        # use the default layout if none is specified
        if fpath_config is None:
            fpath_config = FPATH_DEFAULT_LAYOUT

        fpath_config = Path(fpath_config)
        if not fpath_config.exists():
            raise FileNotFoundError(f"Layout config file not found: {fpath_config}")

        # load the config
        config = LayoutConfig(**load_json(fpath_config))

        self.dpath_root = Path(dpath_root)
        self.fpath_spec = Path(fpath_config)
        self.config = config
        self.dpath_nipoppy = self.dpath_root / NIPOPPY_DIR_NAME

        # directories (for type hinting)
        self.dpath_bids: Path
        self.dpath_derivatives: Path
        self.dpath_sourcedata: Path
        self.dpath_src_tabular: Path
        self.dpath_src_imaging: Path
        self.dpath_downloads: Path
        self.dpath_pre_reorg: Path
        self.dpath_post_reorg: Path
        self.dpath_code: Path
        self.dpath_hpc: Path
        self.dpath_pipelines: Path
        self.dpath_containers: Path
        self.dpath_scratch: Path
        self.dpath_work: Path
        self.dpath_pybids_db: Path
        self.dpath_logs: Path
        self.dpath_tabular: Path
        self.dpath_assessments: Path

        # files (for type hinting)
        self.fpath_config: Path
        self.fpath_curation_status: Path
        self.fpath_manifest: Path
        self.fpath_processing_status: Path
        self.fpath_demographics: Path

    def get_full_path(self, path: StrOrPathLike) -> Path:
        """Build a full path from a relative path."""
        return self.dpath_root / path

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError as exception:
            if name in self.config.path_labels:
                return self.get_full_path(self.config.get_path_info(name).path)
            else:
                raise exception

    def get_paths(self, directory=True, include_optional=False) -> list[Path]:
        """Return a list of all directory or file paths."""
        paths = [
            self.get_full_path(path_info.path)
            for path_info in self.config.path_infos
            if directory == path_info._is_directory
            and (include_optional or path_info._is_required)
        ]
        return paths

    @cached_property
    def dpath_descriptions(self) -> list[Tuple[Path, str]]:
        """Return a list of directory paths and associated description strings."""
        info_list = [
            (self.get_full_path(path_info.path), path_info.description)
            for path_info in self.config.path_infos
            if path_info._is_directory and path_info.description is not None
        ]
        return info_list

    def _find_missing_paths(self) -> list[Path]:
        """Return a list of missing paths."""
        missing = [
            dpath
            for dpath in self.get_paths(directory=True, include_optional=False)
            if not dpath.exists()
        ]
        for fpath in self.get_paths(directory=False, include_optional=False):
            if not fpath.exists():
                missing.append(fpath)
        return missing

    def validate(self) -> bool:
        """Validate that all the expected paths exist."""
        missing_paths = self._find_missing_paths()
        if len(missing_paths) != 0:
            raise FileNotFoundError(
                "Dataset does not follow expected directory structure. "
                f"Missing {len(missing_paths)} paths"
                f": {[str(path) for path in missing_paths]}"
            )
        return True

    def get_dpath_pipeline(self, pipeline_name: str, pipeline_version: str) -> Path:
        """Return the path to a pipeline's derivatives directory."""
        return self.dpath_derivatives / pipeline_name / pipeline_version

    def get_dpath_pipeline_work(
        self,
        pipeline_name: str,
        pipeline_version: str,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Path:
        """Return the path to a pipeline's working directory."""
        return (
            self.dpath_work
            / get_pipeline_tag(pipeline_name, pipeline_version)
            / get_pipeline_tag(
                pipeline_name,
                pipeline_version,
                participant_id=participant_id,
                session_id=session_id,
            )
        )

    def get_dpath_pipeline_output(
        self, pipeline_name: str, pipeline_version: str
    ) -> Path:
        """
        Return the path to a pipeline's output directory.

        Note: This path is the same given a pipeline name and version
        (i.e. does not depend on participant or session).
        """
        return (
            self.get_dpath_pipeline(pipeline_name, pipeline_version)
            / self.dname_pipeline_output
        )

    def get_dpath_pipeline_idp(self, pipeline_name: str, pipeline_version: str) -> Path:
        """
        Return the path to a pipeline's IDPs directory.

        Note: This path is the same given a pipeline name and version
        (i.e. does not depend on participant or session).
        """
        return (
            self.get_dpath_pipeline(pipeline_name, pipeline_version)
            / self.dname_pipeline_idp
        )

    def get_dpath_pybids_db(
        self,
        pipeline_name: str,
        pipeline_version: str,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Path:
        """Return the path to a pipeline's BIDS database directory."""
        dname = get_pipeline_tag(
            pipeline_name,
            pipeline_version,
            participant_id=participant_id,
            session_id=session_id,
        )
        return self.dpath_pybids_db / dname

    def get_dpath_pipeline_store(self, pipeline_type: PipelineTypeEnum) -> Path:
        """Return the path to the pipeline store directory."""
        return self.dpath_pipelines / self.pipeline_type_to_dname_map[pipeline_type]

    def get_dpath_pipeline_bundle(
        self, pipeline_type: PipelineTypeEnum, pipeline_name: str, pipeline_version: str
    ) -> Path:
        """Return the path to the pipeline bundle directory."""
        return self.get_dpath_pipeline_store(pipeline_type) / get_pipeline_tag(
            pipeline_name, pipeline_version
        )


# for printing defaults in docs
DEFAULT_LAYOUT_INFO = DatasetLayout(dpath_root="<NIPOPPY_PROJECT_ROOT>")
