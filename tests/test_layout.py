"""Tests for dataset layout class."""
from pathlib import Path

import pytest

from nipoppy.layout import DatasetLayout

ATTR_TO_DPATH_MAP = {
    "dpath_bids": "bids",
    "dpath_derivatives": "derivatives",
    "dpath_dicom": "dicom",
    "dpath_downloads": "downloads",
    "dpath_proc": "proc",
    "dpath_scratch": "scratch",
    "dpath_raw_dicom": "scratch/raw_dicom",
    "dpath_logs": "scratch/logs",
    "dpath_tabular": "tabular",
    "dpath_assessments": "tabular/assessments",
    "dpath_demographics": "tabular/demographics",
}

ATTR_TO_FPATH_MAP = {
    "fpath_config": "global_configs.json",
    "fpath_doughnut": "scratch/raw_dicom/doughnut.csv",
    "fpath_manifest": "tabular/manifest.csv",
}


@pytest.fixture(params=["my_dataset", "dataset_dir"])
def dpath_root(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    """Dataset root."""
    return tmp_path / request.param


@pytest.mark.parametrize("dataset_root", ["my_dataset", "dataset_dir"])
def test_layout_init(dataset_root):
    """Test layout initialization."""
    layout = DatasetLayout(dpath_root=dataset_root)
    for attr, path in {**ATTR_TO_DPATH_MAP, **ATTR_TO_FPATH_MAP}.items():
        assert getattr(layout, attr) == Path(dataset_root) / path


def test_layout_create(dpath_root: Path):
    """Test layout creation."""
    layout = DatasetLayout(dpath_root=dpath_root)
    layout.create()
    for path in ATTR_TO_DPATH_MAP.values():
        assert Path(dpath_root / path).exists()


def test_layout_create_error(dpath_root: Path):
    """Check that an error is raised if the dataset already exists."""
    dpath_root.mkdir()
    layout = DatasetLayout(dpath_root=dpath_root)
    with pytest.raises(FileExistsError, match="Dataset already exists"):
        layout.create()
