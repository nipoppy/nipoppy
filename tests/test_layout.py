"""Tests for dataset layout class."""
from pathlib import Path

import pytest

from nipoppy.layout import DatasetLayout

ATTR_TO_PATH_MAP = {
    "dpath_bids": "bids",
    "dpath_derivatives": "derivatives",
    "dpath_dicom": "dicom",
    "dpath_downloads": "downloads",
    "dpath_proc": "proc",
    "fpath_config": "global_configs.json",
    "dpath_scratch": "scratch",
    "dpath_raw_dicom": "scratch/raw_dicom",
    "fpath_doughnut": "scratch/raw_dicom/doughnut.csv",
    "dpath_logs": "scratch/logs",
    "dpath_tabular": "tabular",
    "dpath_assessments": "tabular/assessments",
    "dpath_demographics": "tabular/demographics",
    "fpath_manifest": "tabular/manifest.csv",
}


@pytest.mark.parametrize("dataset_root", ["my_dataset", "dataset_dir"])
def test_layout_init(dataset_root):
    """Test layout initialization."""
    layout = DatasetLayout(dataset_root=dataset_root)
    for attr, path in ATTR_TO_PATH_MAP.items():
        assert getattr(layout, attr) == Path(dataset_root) / path
