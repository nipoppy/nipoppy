"""Dataset layout."""
from pathlib import Path


class DatasetLayout:
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
        self.fpath_config = self.dpath_root / "global_configs.json"

        self.dpath_scratch = self.dpath_root / "scratch"
        self.dpath_raw_dicom = self.dpath_scratch / "raw_dicom"
        self.fpath_doughnut = self.dpath_raw_dicom / "doughnut.csv"
        self.dpath_logs = self.dpath_scratch / "logs"

        self.dpath_tabular = self.dpath_root / "tabular"
        self.dpath_assessments = self.dpath_tabular / "assessments"
        self.dpath_demographics = self.dpath_tabular / "demographics"
        self.fpath_manifest = self.dpath_tabular / "manifest.csv"

    def create(self):
        """Create an empty dataset."""
        if self.dpath_root.exists():
            raise FileExistsError(f"Dataset already exists: {self.dpath_root}")

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
        for dpath in dpaths:
            dpath.mkdir(parents=True, exist_ok=True)
