"""Tests for the dataset init workflow."""

from pathlib import Path

import pytest
from conftest import ATTR_TO_DPATH_MAP, FPATH_CONFIG, FPATH_MANIFEST

from nipoppy.workflows.dataset_init import DatasetInitWorkflow


@pytest.fixture(params=["my_dataset", "dataset_dir"])
def dpath_root(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return tmp_path / request.param


def test_init(dpath_root: Path):
    workflow = DatasetInitWorkflow(dpath_root=dpath_root)
    workflow.run()
    for path in ATTR_TO_DPATH_MAP.values():
        assert Path(dpath_root, path).exists()
    assert Path(dpath_root, FPATH_CONFIG).exists()
    assert Path(dpath_root, FPATH_MANIFEST).exists()


def test_init_error(dpath_root: Path):
    dpath_root.mkdir(parents=True)
    workflow = DatasetInitWorkflow(dpath_root=dpath_root)
    with pytest.raises(FileExistsError, match="Dataset directory already exists"):
        workflow.run()
