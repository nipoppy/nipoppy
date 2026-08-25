"""Tests for the TrackCurationWorkflow."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.workflows.track_curation import TrackCurationWorkflow
from tests.conftest import create_empty_dataset, get_config, prepare_dataset


@pytest.fixture(scope="function")
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)
    workflow = TrackCurationWorkflow(dpath_root=dpath_root)
    workflow.study.config = get_config()
    workflow.study.config.save(workflow.study.layout.fpath_config)

    manifest = prepare_dataset(
        participants_and_sessions_manifest={"01": ["BL", "M12"], "02": ["BL", "M12"]},
    )
    workflow.study.manifest = manifest
    return workflow


def test_run_main_without_existing_curation_status_file(
    workflow: TrackCurationWorkflow,
    mocker: pytest_mock.MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    workflow.study.layout.fpath_curation_status.unlink(missing_ok=True)
    assert not workflow.study.layout.fpath_curation_status.exists()

    curation_status_table = CurationStatusTable()
    mocked_generate_curation_status_table = mocker.patch(
        "nipoppy.workflows.track_curation.generate_curation_status_table",
        return_value=curation_status_table,
    )
    mocked_save_with_backup = mocker.patch.object(
        curation_status_table, "save_with_backup"
    )

    workflow.run_main()

    mocked_generate_curation_status_table.assert_called_once_with(
        manifest=workflow.study.manifest,
        dicom_dir_map=workflow.dicom_dir_map,
        dpath_downloaded=workflow.study.layout.dpath_pre_reorg,
        dpath_organized=workflow.study.layout.dpath_post_reorg,
        dpath_bidsified=workflow.study.layout.dpath_bids,
    )
    mocked_save_with_backup.assert_called_once_with(
        workflow.study.layout.fpath_curation_status,
        dry_run=workflow.dry_run,
    )
    assert (
        "Successfully generated/updated the dataset's curation status file"
        in caplog.text
    )


def test_run_main_overwrites_existing_curation_status_file(
    workflow: TrackCurationWorkflow,
    mocker: pytest_mock.MockerFixture,
):
    old_curation_status_table = CurationStatusTable().add_or_update_records(
        [
            {
                CurationStatusTable.col_participant_id: "01",
                CurationStatusTable.col_visit_id: "BL",
                CurationStatusTable.col_session_id: "BL",
                CurationStatusTable.col_datatype: ["anat"],
                CurationStatusTable.col_participant_dicom_dir: "01/BL",
                CurationStatusTable.col_in_pre_reorg: True,
                CurationStatusTable.col_in_post_reorg: True,
                CurationStatusTable.col_in_bids: True,
            },
        ]
    )
    old_curation_status_table.save_with_backup(
        workflow.study.layout.fpath_curation_status
    )

    new_curation_status_table = CurationStatusTable()
    mocked_generate_curation_status_table = mocker.patch(
        "nipoppy.workflows.track_curation.generate_curation_status_table",
        return_value=new_curation_status_table,
    )

    workflow.run_main()

    mocked_generate_curation_status_table.assert_called_once_with(
        manifest=workflow.study.manifest,
        dicom_dir_map=workflow.dicom_dir_map,
        dpath_downloaded=workflow.study.layout.dpath_pre_reorg,
        dpath_organized=workflow.study.layout.dpath_post_reorg,
        dpath_bidsified=workflow.study.layout.dpath_bids,
    )
    assert CurationStatusTable.load(workflow.study.layout.fpath_curation_status).equals(
        new_curation_status_table
    )
