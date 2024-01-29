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


@pytest.mark.parametrize("dpath_root", ["my_dataset", "dataset_dir"])
def test_layout_init(dpath_root):
    """Test layout initialization."""
    layout = DatasetLayout(dpath_root=dpath_root)
    for attr, path in {**ATTR_TO_DPATH_MAP, **ATTR_TO_FPATH_MAP}.items():
        assert getattr(layout, attr) == Path(dpath_root) / path


def test_layout_dpaths(dpath_root: Path):
    """Test layout creation."""
    layout = DatasetLayout(dpath_root=dpath_root)
    dpaths = layout.dpaths
    for path in ATTR_TO_DPATH_MAP.values():
        assert Path(dpath_root / path) in dpaths
