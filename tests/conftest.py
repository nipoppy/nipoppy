"""Utilities for tests."""
from pathlib import Path

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

DPATH_TEST_DATA = Path(__file__).parent / "data"
