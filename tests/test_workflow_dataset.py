"""Tests for the BaseDatasetWorkflow class."""

import logging
import shutil
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.main import Config
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import FPATH_SAMPLE_CONFIG, FPATH_SAMPLE_MANIFEST
from nipoppy.workflows.base import BaseDatasetWorkflow

from .conftest import DPATH_TEST_DATA, create_empty_dataset, get_config, prepare_dataset


@pytest.fixture()
def workflow(tmp_path: Path):
    class DummyWorkflow(BaseDatasetWorkflow):
        def run_main(self):
            pass

    dpath_root = tmp_path / "my_dataset"
    workflow = DummyWorkflow(dpath_root=dpath_root, name="my_workflow")
    workflow.logger.setLevel(logging.DEBUG)  # capture all logs

    create_empty_dataset(workflow.dpath_root)
    get_config().save(workflow.layout.fpath_config)

    manifest = prepare_dataset(participants_and_sessions_manifest={})
    manifest.save_with_backup(workflow.layout.fpath_manifest)
    return workflow


def test_abstract_class():
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseDatasetWorkflow(None, None)


def test_init(workflow: BaseDatasetWorkflow):
    assert isinstance(workflow.dpath_root, Path)


def test_generate_fpath_log(
    workflow: BaseDatasetWorkflow, datetime_fixture
):  # noqa F811
    fpath_log = workflow.generate_fpath_log()
    assert isinstance(fpath_log, Path)
    assert (
        fpath_log
        == workflow.layout.dpath_logs / "my_workflow/my_workflow-20240404_1234.log"
    )


@pytest.mark.parametrize("fname_stem", ["123", "test", "my_workflow"])
def test_generate_fpath_log_custom(
    fname_stem,
    workflow: BaseDatasetWorkflow,
    datetime_fixture,  # noqa F811
):
    fpath_log = workflow.generate_fpath_log(fname_stem=fname_stem)
    assert isinstance(fpath_log, Path)
    assert (
        fpath_log
        == workflow.layout.dpath_logs / f"my_workflow/{fname_stem}-20240404_1234.log"
    )


@pytest.mark.parametrize("skip_logging", [True, False])
def test_run_setup_logfile(
    workflow: BaseDatasetWorkflow, skip_logging, mocker: pytest_mock.MockFixture
):
    fpath_log = workflow.dpath_root / "my_workflow.log"
    mocked_generate_fpath_log = mocker.patch.object(
        workflow, "generate_fpath_log", return_value=fpath_log
    )
    mocked_add_logfile = mocker.patch("nipoppy.workflows.base.add_logfile")
    workflow._skip_logging = skip_logging
    workflow.run_setup()

    if skip_logging:
        mocked_generate_fpath_log.assert_not_called()
        mocked_add_logfile.assert_not_called()
    else:
        mocked_generate_fpath_log.assert_called_once()
        mocked_add_logfile.assert_called_once_with(workflow.logger, fpath_log)


@pytest.mark.parametrize(
    "fpath_config",
    [
        FPATH_SAMPLE_CONFIG,
        DPATH_TEST_DATA / "config1.json",
        DPATH_TEST_DATA / "config2.json",
        DPATH_TEST_DATA / "config3.json",
    ],
)
def test_config(workflow: BaseDatasetWorkflow, fpath_config):
    workflow.layout.fpath_config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(fpath_config, workflow.layout.fpath_config)
    assert isinstance(workflow.config, Config)


def test_config_not_found(workflow: BaseDatasetWorkflow):
    workflow.layout.fpath_config.unlink()
    with pytest.raises(FileNotFoundError):
        workflow.config


def test_config_replacement(workflow: BaseDatasetWorkflow):
    config = get_config(dataset_name="[[NIPOPPY_DPATH_ROOT]]")
    config.save(workflow.layout.fpath_config)
    assert str(workflow.config.DATASET_NAME) == str(workflow.dpath_root)


def test_manifest(workflow: BaseDatasetWorkflow):
    workflow.layout.fpath_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FPATH_SAMPLE_MANIFEST, workflow.layout.fpath_manifest)
    config = get_config(
        visit_ids=["BL", "M12"],
    )
    workflow.layout.fpath_config.parent.mkdir(parents=True, exist_ok=True)
    config.save(workflow.layout.fpath_config)
    assert isinstance(workflow.manifest, Manifest)


def test_manifest_not_found(workflow: BaseDatasetWorkflow):
    workflow.layout.fpath_manifest.unlink()
    with pytest.raises(FileNotFoundError):
        workflow.manifest


def test_dicom_dir_map(workflow: BaseDatasetWorkflow):
    workflow.config = get_config()
    assert isinstance(workflow.dicom_dir_map, DicomDirMap)


def test_dicom_dir_map_custom(workflow: BaseDatasetWorkflow):
    workflow.config = get_config()
    workflow.config.DICOM_DIR_MAP_FILE = DPATH_TEST_DATA / "dicom_dir_map1.tsv"
    assert isinstance(workflow.dicom_dir_map, DicomDirMap)


def test_dicom_dir_map_not_found(workflow: BaseDatasetWorkflow):
    workflow.config = get_config()
    workflow.config.DICOM_DIR_MAP_FILE = "fake_path"
    with pytest.raises(FileNotFoundError, match="DICOM directory map file not found"):
        workflow.dicom_dir_map


def test_bagel_empty_if_not_found(workflow: BaseDatasetWorkflow):
    assert not workflow.layout.fpath_imaging_bagel.exists()
    assert len(workflow.bagel) == 0
