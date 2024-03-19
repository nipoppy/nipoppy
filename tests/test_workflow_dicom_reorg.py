"""Tests for DicomReorgWorkflow."""

from pathlib import Path

import pytest
from conftest import _prepare_dataset

from nipoppy.config import Config
from nipoppy.tabular.manifest import Manifest
from nipoppy.workflows.dicom_reorg import DicomReorgWorkflow


@pytest.mark.parametrize(
    "participants_and_sessions_manifest,participants_and_sessions_downloaded",
    [
        (
            {
                "S01": ["ses-1", "ses-2", "ses-3"],
                "S02": ["ses-1", "ses-2", "ses-3"],
                "S03": ["ses-1", "ses-2", "ses-3"],
            },
            {
                "S01": ["ses-1", "ses-2", "ses-3"],
                "S02": ["ses-1", "ses-2"],
                "S03": ["ses-3"],
            },
        ),
        (
            {
                "P01": ["ses-BL"],
                "P02": ["ses-V01"],
                "P03": ["ses-V03"],
            },
            {
                "P01": ["ses-BL"],
                "P02": ["ses-BL", "ses-V01"],
                "P03": ["ses-BL", "ses-V03"],
            },
        ),
    ],
)
@pytest.mark.parametrize("copy_files", [True, False])
def test_dicom_reorg_workflow(
    participants_and_sessions_manifest: dict,
    participants_and_sessions_downloaded: dict,
    copy_files: bool,
    tmp_path: Path,
):
    dataset_name = "my_dataset"
    workflow = DicomReorgWorkflow(
        dpath_root=tmp_path / dataset_name, copy_files=copy_files
    )

    manifest: Manifest = _prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        dpath_downloaded=workflow.layout.dpath_raw_dicom,
    )

    config = Config(
        DATASET_NAME=dataset_name,
        SESSIONS=manifest[manifest.col_session].unique(),
        PROC_PIPELINES={},
    )

    manifest.save_with_backup(workflow.layout.fpath_manifest)
    config.save(workflow.layout.fpath_config)

    workflow.run()

    for participant, sessions in participants_and_sessions_manifest.items():
        for session in sessions:
            dpath_to_check: Path = workflow.layout.dpath_dicom / participant / session

            if (
                participant in participants_and_sessions_downloaded
                and session in participants_and_sessions_downloaded[participant]
            ):
                # check that directory exists
                assert dpath_to_check.exists()

                # make sure it is not empty
                # and that symlinks are created if requested
                count = 0
                for fpath in dpath_to_check.iterdir():
                    if copy_files:
                        assert not fpath.is_symlink()
                    else:
                        assert fpath.is_symlink()
                    count += 1
                assert count > 0

                # check that the doughnut has been updated
                assert workflow.doughnut.get_status(
                    participant, session, workflow.doughnut.col_organized
                )

            else:
                assert not dpath_to_check.exists()


def test_dicom_reorg_workflow_run_single_error_file_exists(tmp_path: Path):
    participant = "01"
    session = "ses-1"
    participants_and_sessions = {participant: [session]}
    dataset_name = "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=tmp_path / dataset_name)

    manifest: Manifest = _prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_downloaded=participants_and_sessions,
        dpath_downloaded=workflow.layout.dpath_raw_dicom,
    )

    config = Config(
        DATASET_NAME=dataset_name,
        SESSIONS=manifest[manifest.col_session].unique(),
        PROC_PIPELINES={},
    )

    manifest.save_with_backup(workflow.layout.fpath_manifest)
    config.save(workflow.layout.fpath_config)

    # create the same file in both the downloaded and organized directories
    fname = "test.dcm"
    for fpath in [
        workflow.layout.dpath_raw_dicom / session / participant / fname,
        workflow.layout.dpath_dicom / participant / session / fname,
    ]:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    with pytest.raises(FileExistsError, match="Cannot move file"):
        workflow.run_single(participant, session)


def test_dicom_reorg_workflow_run_single_error_no_data(tmp_path: Path):
    participant = "01"
    session = "ses-1"
    participants_and_sessions = {participant: [session]}
    dataset_name = "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=tmp_path / dataset_name)

    manifest: Manifest = _prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_downloaded=participants_and_sessions,
        dpath_downloaded=workflow.layout.dpath_raw_dicom,
    )

    config = Config(
        DATASET_NAME=dataset_name,
        SESSIONS=manifest[manifest.col_session].unique(),
        PROC_PIPELINES={},
    )

    manifest.save_with_backup(workflow.layout.fpath_manifest)
    config.save(workflow.layout.fpath_config)

    # create the same file in both the downloaded and organized directories
    fname = "test.dcm"
    for fpath in [
        workflow.layout.dpath_raw_dicom / session / participant / fname,
        workflow.layout.dpath_dicom / participant / session / fname,
    ]:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    with pytest.raises(FileNotFoundError, match="Raw DICOM directory not found"):
        workflow.run_single("XXX", "ses-X")
