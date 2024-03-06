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
        ["sourcedata", "downloads"],
        ["rawdata", "derivatives"],
        [
            "code",
            "code/containers",
            "code/descriptors",
            "code/invocations",
            "code/scripts",
            "code/global_configs.json",
            "code/pybids",
            "code/pybids/bids_db",
            "code/pybids/ignore_patterns",
        ],
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
        ["sourcedata", "downloads"],
        ["rawdata", "derivatives"],
        ["code", "code/global_configs.json"],
        [
            "code",
            "code/containers",
            "code/descriptors",
            "code/invocations",
            "code/scripts",
            "code/global_configs.json",
            "code/pybids",
            "code/pybids/bids_db",
            "code/pybids/ignore_patterns",
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


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,expected",
    [
        ("my_pipeline", "v1", "derivatives/my_pipeline-v1"),
        ("pipeline", "v2", "derivatives/pipeline-v2"),
    ],
)
def test_get_dpath_pipeline(
    dpath_root: Path, pipeline_name, pipeline_version, expected
):
    layout = DatasetLayout(dpath_root=dpath_root)
    assert (
        layout.get_dpath_pipeline(
            pipeline_name=pipeline_name, pipeline_version=pipeline_version
        )
        == dpath_root / expected
    )


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,participant,session,expected",
    [
        (
            "my_pipeline",
            "v1",
            None,
            None,
            "derivatives/my_pipeline-v1/work/my_pipeline-v1",
        ),
        (
            "pipeline",
            "v2",
            "3000",
            None,
            "derivatives/pipeline-v2/work/pipeline-v2-3000",
        ),
        (
            "pipeline",
            "v2",
            None,
            "ses-BL",
            "derivatives/pipeline-v2/work/pipeline-v2-BL",
        ),
        (
            "pipeline",
            "v2",
            "01",
            "1",
            "derivatives/pipeline-v2/work/pipeline-v2-01-1",
        ),
    ],
)
def test_get_dpath_pipeline_work(
    dpath_root: Path, pipeline_name, pipeline_version, participant, session, expected
):
    layout = DatasetLayout(dpath_root=dpath_root)
    assert (
        layout.get_dpath_pipeline_work(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            participant=participant,
            session=session,
        )
        == dpath_root / expected
    )


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,expected",
    [
        ("my_pipeline", "v1", "derivatives/my_pipeline-v1/output"),
        ("pipeline", "v2", "derivatives/pipeline-v2/output"),
    ],
)
def test_get_dpath_pipeline_output(
    dpath_root: Path, pipeline_name, pipeline_version, expected
):
    layout = DatasetLayout(dpath_root=dpath_root)
    assert (
        layout.get_dpath_pipeline_output(
            pipeline_name=pipeline_name, pipeline_version=pipeline_version
        )
        == dpath_root / expected
    )


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,participant,session,expected",
    [
        ("my_pipeline", "v1", None, None, "code/pybids/bids_db/my_pipeline-v1"),
        ("pipeline", "v2", "01", "ses-1", "code/pybids/bids_db/pipeline-v2-01-1"),
    ],
)
def test_get_dpath_bids_db(
    dpath_root: Path, pipeline_name, pipeline_version, participant, session, expected
):
    layout = DatasetLayout(dpath_root=dpath_root)
    assert (
        layout.get_dpath_bids_db(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            participant=participant,
            session=session,
        )
        == dpath_root / expected
    )
