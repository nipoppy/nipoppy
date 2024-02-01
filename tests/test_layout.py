"""Tests for dataset layout class."""
import shutil
from pathlib import Path

import pytest
from conftest import ATTR_TO_DPATH_MAP, ATTR_TO_FPATH_MAP

from nipoppy.layout import DatasetLayout


@pytest.fixture(params=["my_dataset", "dataset_dir"])
def dpath_root(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return tmp_path / request.param


def _create_valid_dataset(dpath_root: Path):
    for dpath in ATTR_TO_DPATH_MAP.values():
        (dpath_root / dpath).mkdir(parents=True, exist_ok=True)
    for fpath in ATTR_TO_FPATH_MAP.values():
        (dpath_root / fpath).touch()


def _create_invalid_dataset(dpath_root: Path, paths_to_delete: list[str]):
    _create_valid_dataset(dpath_root)
    for path in paths_to_delete:
        shutil.rmtree(dpath_root / path, ignore_errors=True)


@pytest.mark.parametrize("dpath_root", ["my_dataset", "dataset_dir"])
def test_init(dpath_root):
    layout = DatasetLayout(dpath_root=dpath_root)
    for attr, path in {**ATTR_TO_DPATH_MAP, **ATTR_TO_FPATH_MAP}.items():
        assert getattr(layout, attr) == Path(dpath_root) / path


def test_dpaths(dpath_root: Path):
    layout = DatasetLayout(dpath_root=dpath_root)
    dpaths = layout.dpaths
    for path in ATTR_TO_DPATH_MAP.values():
        assert Path(dpath_root / path) in dpaths


def test_fpaths(dpath_root: Path):
    layout = DatasetLayout(dpath_root=dpath_root)
    fpaths = layout.fpaths
    for path in ATTR_TO_FPATH_MAP.values():
        assert Path(dpath_root / path) in fpaths


@pytest.mark.parametrize(
    "paths_to_delete",
    [
        [],
        ["dicom", "downloads"],
        ["bids", "derivatives"],
        ["proc", "proc/global_configs.json"],
        [
            "scratch",
            "scratch/logs",
            "scratch/raw_dicom",
            "scratch/raw_dicom/doughnut.csv",
        ],
        [
            "tabular",
            "tabular/manifest.csv",
            "tabular/assessments",
            "tabular/demographics",
        ],
    ],
)
def test_find_missing_paths(dpath_root: Path, paths_to_delete: list[str]):
    _create_invalid_dataset(dpath_root, paths_to_delete)
    layout = DatasetLayout(dpath_root=dpath_root)
    assert len(layout._find_missing_paths()) == len(paths_to_delete)


def test_validate(dpath_root: Path):
    _create_valid_dataset(dpath_root)
    assert DatasetLayout(dpath_root=dpath_root).validate()


@pytest.mark.parametrize(
    "paths_to_delete",
    [
        ["dicom", "downloads"],
        ["bids", "derivatives"],
        ["proc", "proc/global_configs.json"],
        [
            "scratch",
            "scratch/logs",
            "scratch/raw_dicom",
            "scratch/raw_dicom/doughnut.csv",
        ],
        [
            "tabular",
            "tabular/manifest.csv",
            "tabular/assessments",
            "tabular/demographics",
        ],
    ],
)
def test_validate_error(dpath_root: Path, paths_to_delete: list[str]):
    _create_invalid_dataset(dpath_root, paths_to_delete)
    layout = DatasetLayout(dpath_root=dpath_root)
    with pytest.raises(FileNotFoundError, match="Missing"):
        layout.validate()
