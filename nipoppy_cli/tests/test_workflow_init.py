"""Tests for the dataset init workflow."""

from pathlib import Path

import pytest

from nipoppy.utils import DPATH_LAYOUTS
from nipoppy.workflows.dataset_init import InitWorkflow

from .conftest import ATTR_TO_DPATH_MAP, FPATH_CONFIG, FPATH_MANIFEST


@pytest.fixture(params=["my_dataset", "dataset_dir"])
def dpath_root(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return tmp_path / request.param


def test_run(dpath_root: Path):
    workflow = InitWorkflow(dpath_root=dpath_root)
    workflow.run()
    for path in ATTR_TO_DPATH_MAP.values():
        assert Path(dpath_root, path).exists()
        assert Path(dpath_root, path, "README.md").exists()
    assert Path(dpath_root, FPATH_CONFIG).exists()
    assert Path(dpath_root, FPATH_MANIFEST).exists()


def test_run_error(dpath_root: Path):
    dpath_root.mkdir(parents=True)
    workflow = InitWorkflow(dpath_root=dpath_root)
    with pytest.raises(FileExistsError, match="Dataset directory already exists"):
        workflow.run()


def test_custom_layout(dpath_root: Path):
    workflow = InitWorkflow(
        dpath_root=dpath_root, fpath_layout=DPATH_LAYOUTS / "layout-0.1.0.json"
    )
    workflow.run()

    # check some of the paths from the old spec exist
    assert (dpath_root / "proc").exists()
    assert (dpath_root / "dicom").exists()


@pytest.mark.parametrize("attr", ["config", "manifest", "doughnut"])
def test_config_attrs_error(attr):
    with pytest.raises(
        RuntimeError,
        match="The config property .* is not available*",
    ):
        getattr(InitWorkflow(dpath_root="my_dataset"), attr)
