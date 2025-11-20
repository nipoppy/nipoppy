"""Tests for the BaseDatasetWorkflow class."""

import shutil
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.main import Config
from nipoppy.exceptions import FileOperationError
from nipoppy.layout import LayoutError
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils.utils import FPATH_SAMPLE_CONFIG, FPATH_SAMPLE_MANIFEST
from nipoppy.workflows.base import BaseDatasetWorkflow
from tests.conftest import (
    DPATH_TEST_DATA,
    create_empty_dataset,
    get_config,
    prepare_dataset,
)


@pytest.fixture()
def workflow(tmp_path: Path):
    class DummyWorkflow(BaseDatasetWorkflow):
        def run_main(self):
            pass

    dpath_root = tmp_path / "my_dataset"
    workflow = DummyWorkflow(dpath_root=dpath_root, name="my_workflow")

    create_empty_dataset(workflow.dpath_root)

    # save a config but do not set workflow.config yet
    # because some tests check what happens when the config loaded
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


@pytest.mark.parametrize("skip_logfile", [True, False])
def test_run_setup_logfile(
    workflow: BaseDatasetWorkflow, skip_logfile, mocker: pytest_mock.MockFixture
):
    fpath_log = workflow.dpath_root / "my_workflow.log"
    mocked_generate_fpath_log = mocker.patch.object(
        workflow, "generate_fpath_log", return_value=fpath_log
    )
    mocked_add_file_handler = mocker.patch(
        "nipoppy.workflows.base.logger.add_file_handler"
    )
    workflow._skip_logfile = skip_logfile
    workflow.run_setup()

    if skip_logfile:
        mocked_generate_fpath_log.assert_not_called()
        mocked_add_file_handler.assert_not_called()
    else:
        mocked_generate_fpath_log.assert_called_once()
        mocked_add_file_handler.assert_called_once_with(fpath_log)


def test_run_setup_validation_before_logfile(workflow: BaseDatasetWorkflow):
    # delete required directory
    workflow.layout.dpath_bids.rmdir()

    # expect layout validation error
    with pytest.raises(
        LayoutError, match="Dataset does not follow expected directory structure"
    ):
        workflow.run_setup()

    # make sure no logfile is created
    assert list(workflow.layout.dpath_logs.iterdir()) == []


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
    with pytest.raises(FileOperationError):
        workflow.config


def test_config_replacement(workflow: BaseDatasetWorkflow):
    # overwrite existing config file
    config = get_config(dicom_dir_map_file="[[NIPOPPY_DPATH_ROOT]]")
    config.save(workflow.layout.fpath_config)
    assert str(workflow.config.DICOM_DIR_MAP_FILE) == str(workflow.dpath_root)


def test_manifest(workflow: BaseDatasetWorkflow):
    workflow.layout.fpath_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FPATH_SAMPLE_MANIFEST, workflow.layout.fpath_manifest)
    assert isinstance(workflow.manifest, Manifest)


def test_manifest_not_found(workflow: BaseDatasetWorkflow):
    workflow.layout.fpath_manifest.unlink()
    with pytest.raises(FileOperationError):
        workflow.manifest


def test_dicom_dir_map(workflow: BaseDatasetWorkflow):
    assert isinstance(workflow.dicom_dir_map, DicomDirMap)


def test_dicom_dir_map_custom(workflow: BaseDatasetWorkflow):
    workflow.config.DICOM_DIR_MAP_FILE = DPATH_TEST_DATA / "dicom_dir_map1.tsv"
    assert isinstance(workflow.dicom_dir_map, DicomDirMap)


def test_dicom_dir_map_not_found(workflow: BaseDatasetWorkflow):
    workflow.config.DICOM_DIR_MAP_FILE = "fake_path"
    with pytest.raises(FileOperationError, match="DICOM directory map file not found"):
        workflow.dicom_dir_map


def test_bagel_empty_if_not_found(workflow: BaseDatasetWorkflow):
    assert not workflow.layout.fpath_curation_status.exists()
    assert len(workflow.curation_status_table) == 0
