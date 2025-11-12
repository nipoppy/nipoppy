"""Tests for the BaseDatasetWorkflow class."""

import logging
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.dicom_dir_map import DicomDirMap
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
    workflow.logger.setLevel(logging.DEBUG)  # capture all logs

    create_empty_dataset(workflow.dpath_root)

    # save a config but do not set workflow.study.config yet
    # because some tests check what happens when the config loaded
    get_config().save(workflow.study.layout.fpath_config)

    manifest = prepare_dataset(participants_and_sessions_manifest={})
    manifest.save_with_backup(workflow.study.layout.fpath_manifest)
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
    assert fpath_log == workflow.study.layout.dpath_logs.joinpath(
        "my_workflow/my_workflow-20240404_1234.log"
    )


@pytest.mark.parametrize("fname_stem", ["123", "test", "my_workflow"])
def test_generate_fpath_log_custom(
    fname_stem,
    workflow: BaseDatasetWorkflow,
    datetime_fixture,  # noqa F811
):
    fpath_log = workflow.generate_fpath_log(fname_stem=fname_stem)
    assert isinstance(fpath_log, Path)
    assert fpath_log == workflow.study.layout.dpath_logs.joinpath(
        f"my_workflow/{fname_stem}-20240404_1234.log"
    )


@pytest.mark.parametrize("skip_logfile", [True, False])
def test_run_setup_logfile(
    workflow: BaseDatasetWorkflow, skip_logfile, mocker: pytest_mock.MockFixture
):
    fpath_log = workflow.dpath_root / "my_workflow.log"
    mocked_generate_fpath_log = mocker.patch.object(
        workflow, "generate_fpath_log", return_value=fpath_log
    )
    mocked_add_logfile = mocker.patch("nipoppy.workflows.base.add_logfile")
    workflow._skip_logfile = skip_logfile
    workflow.run_setup()

    if skip_logfile:
        mocked_generate_fpath_log.assert_not_called()
        mocked_add_logfile.assert_not_called()
    else:
        mocked_generate_fpath_log.assert_called_once()
        mocked_add_logfile.assert_called_once_with(workflow.logger, fpath_log)


def test_run_setup_validation_before_logfile(workflow: BaseDatasetWorkflow):
    # delete required directory
    workflow.study.layout.dpath_bids.rmdir()

    # expect layout validation error
    with pytest.raises(
        FileNotFoundError, match="Dataset does not follow expected directory structure"
    ):
        workflow.run_setup()

    # make sure no logfile is created
    assert list(workflow.study.layout.dpath_logs.iterdir()) == []


def test_config(workflow: BaseDatasetWorkflow):
    assert id(workflow.study.config) == id(workflow.study.config)


def test_manifest(workflow: BaseDatasetWorkflow):
    assert id(workflow.study.manifest) == id(workflow.study.manifest)


def test_curation_status_file_generated_if_not_found(
    workflow: BaseDatasetWorkflow, mocker: pytest_mock.MockFixture
):
    mocked = mocker.patch(
        "nipoppy.workflows.base.generate_curation_status_table",
        return_value=CurationStatusTable(),
    )
    assert not workflow.study.layout.fpath_curation_status.exists()
    _ = workflow.curation_status_table
    mocked.assert_called_once()
    assert workflow.study.layout.fpath_curation_status.exists()


def test_processing_status_file_empty_if_not_found(workflow: BaseDatasetWorkflow):
    assert not workflow.study.layout.fpath_processing_status.exists()
    assert len(workflow.processing_status_table) == 0


def test_dicom_dir_map(workflow: BaseDatasetWorkflow):
    assert isinstance(workflow.dicom_dir_map, DicomDirMap)


def test_dicom_dir_map_custom(workflow: BaseDatasetWorkflow):
    workflow.study.config.DICOM_DIR_MAP_FILE = DPATH_TEST_DATA / "dicom_dir_map1.tsv"
    assert isinstance(workflow.dicom_dir_map, DicomDirMap)


def test_dicom_dir_map_not_found(workflow: BaseDatasetWorkflow):
    workflow.study.config.DICOM_DIR_MAP_FILE = "fake_path"
    with pytest.raises(FileNotFoundError, match="DICOM directory map file not found"):
        workflow.dicom_dir_map
