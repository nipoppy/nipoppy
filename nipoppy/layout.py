"""Dataset layout."""

from pathlib import Path

from nipoppy.base import _Base
from nipoppy.utils import get_pipeline_tag


class DatasetLayout(_Base):
    """File/directory structure in a dataset."""

    def __init__(self, dpath_root: Path | str):
        """Initialize the object.

        Parameters
        ----------
        dataset_root : Path | str
            Path to the root directory of the dataset.
        """
        self.dpath_root = Path(dpath_root)

        self.dpath_bids = self.dpath_root / "bids"
        self.dpath_derivatives = self.dpath_root / "derivatives"
        self.dpath_dicom = self.dpath_root / "dicom"
        self.dpath_downloads = self.dpath_root / "downloads"
        self.dpath_proc = self.dpath_root / "proc"

        self.dpath_scratch = self.dpath_root / "scratch"
        self.dpath_raw_dicom = self.dpath_scratch / "raw_dicom"
        self.dpath_logs = self.dpath_scratch / "logs"

        self.dpath_tabular = self.dpath_root / "tabular"
        self.dpath_assessments = self.dpath_tabular / "assessments"
        self.dpath_demographics = self.dpath_tabular / "demographics"

        self.fpath_config = self.dpath_proc / "global_configs.json"
        self.fpath_doughnut = self.dpath_raw_dicom / "doughnut.csv"
        self.fpath_manifest = self.dpath_tabular / "manifest.csv"

        self.dname_pipeline_work = "work"
        self.dname_pipeline_output = "output"

    @property
    def dpaths(self) -> list[Path]:
        """Return a list of all directory paths."""
        dpaths = [
            self.dpath_root,
            self.dpath_bids,
            self.dpath_derivatives,
            self.dpath_dicom,
            self.dpath_downloads,
            self.dpath_proc,
            self.dpath_scratch,
            self.dpath_raw_dicom,
            self.dpath_logs,
            self.dpath_tabular,
            self.dpath_assessments,
            self.dpath_demographics,
        ]
        return dpaths

    @property
    def fpaths(self) -> list[Path]:
        """Return a list of all file paths."""
        fpaths = [
            self.fpath_config,
            self.fpath_doughnut,
            self.fpath_manifest,
        ]
        return fpaths

    def _find_missing_paths(self) -> list[Path]:
        """Return a list of missing paths."""
        missing = []
        for dpath in self.dpaths:
            if not dpath.exists():
                missing.append(dpath)
        for fpath in self.fpaths:
            if not fpath.exists():
                missing.append(fpath)
        return missing

    def validate(self) -> bool:
        """Validate that all the expected paths exist."""
        missing_paths = self._find_missing_paths()
        if len(missing_paths) != 0:
            raise FileNotFoundError(
                f"Missing {len(missing_paths)} paths"
                f": {[str(path) for path in missing_paths]}"
            )
        return True

    def get_dpath_pipeline(self, pipeline_name: str, pipeline_version: str) -> Path:
        """Return the path to a pipeline's directory."""
        return self.dpath_derivatives / get_pipeline_tag(
            pipeline_name, pipeline_version
        )

    def get_dpath_pipeline_work(
        self, pipeline_name: str, pipeline_version: str
    ) -> Path:
        """Return the path to a pipeline's working directory."""
        return (
            self.get_dpath_pipeline(pipeline_name, pipeline_version)
            / self.dname_pipeline_work
        )

    def get_dpath_pipeline_output(
        self, pipeline_name: str, pipeline_version: str
    ) -> Path:
        """Return the path to a pipeline's working directory."""
        return (
            self.get_dpath_pipeline(pipeline_name, pipeline_version)
            / self.dname_pipeline_output
        )
