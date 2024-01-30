"""Tests for dataset layout class."""
from pathlib import Path

import pytest
from conftest import ATTR_TO_DPATH_MAP, ATTR_TO_FPATH_MAP

from nipoppy.layout import DatasetLayout


@pytest.fixture(params=["my_dataset", "dataset_dir"])
def dpath_root(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return tmp_path / request.param


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
