"""Tests for the TrackCurationWorkflow."""

from pathlib import Path

import pytest

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.workflows.track_curation import TrackCurationWorkflow
from tests.conftest import (
    check_curation_status_table,
    create_empty_dataset,
    get_config,
    prepare_dataset,
)


@pytest.fixture(scope="function")
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)
    workflow = TrackCurationWorkflow(dpath_root=dpath_root)
    workflow.study.config = get_config()
    workflow.study.config.save(workflow.study.layout.fpath_config)
    return workflow


@pytest.mark.parametrize(
    (
        "participants_and_sessions_manifest1"
        ",participants_and_sessions_manifest2"
        ",participants_and_sessions_downloaded"
        ",participants_and_sessions_organized"
        ",participants_and_sessions_bidsified"
    ),
    [
        (
            {"01": ["BL", "M12"], "02": ["BL", "M12"]},
            {
                "01": ["BL", "M12"],
                "02": ["BL", "M12"],
                "03": ["BL", "M12"],
            },
            {"01": ["BL", "M12"], "02": ["BL"]},
            {"01": ["BL"], "02": ["BL"], "03": ["BL"]},
            {"01": ["BL", "M12"], "03": ["M12"]},
        ),
        (
            {"PD01": ["BL"], "PD02": ["BL"]},
            {"PD01": ["BL", "M12"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL", "M12"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL"], "PD02": ["BL"]},
        ),
    ],
)
@pytest.mark.parametrize("empty", [True, False])
def test_run_main(
    workflow: TrackCurationWorkflow,
    participants_and_sessions_manifest1: dict[str, list[str]],
    participants_and_sessions_manifest2: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_bidsified: dict[str, list[str]],
    empty: bool,
):
    workflow.empty = empty

    # initial manifest
    manifest1 = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_downloaded=workflow.study.layout.dpath_pre_reorg,
        dpath_organized=workflow.study.layout.dpath_post_reorg,
        dpath_bidsified=workflow.study.layout.dpath_bids,
    )
    workflow.study.manifest = manifest1

    # generate the curation status table
    workflow.run_main()
    table1 = CurationStatusTable.load(workflow.study.layout.fpath_curation_status)

    assert len(table1) == len(manifest1)
    check_curation_status_table(
        table=table1,
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )

    # update the manifest (add rows)
    manifest2 = prepare_dataset(participants_and_sessions_manifest2)
    manifest2.save_with_backup(workflow.study.layout.fpath_manifest)

    # update the curation status table
    TrackCurationWorkflow(dpath_root=workflow.dpath_root, empty=empty).run()
    table2 = CurationStatusTable.load(workflow.study.layout.fpath_curation_status)

    assert len(table2) == len(manifest2)
    check_curation_status_table(
        table=table2,
        participants_and_sessions_manifest=participants_and_sessions_manifest2,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )


@pytest.mark.parametrize(
    (
        "participants_and_sessions_manifest"
        ",participants_and_sessions_downloaded"
        ",participants_and_sessions_organized"
        ",participants_and_sessions_bidsified"
    ),
    [
        (
            {"01": ["BL", "M12"], "02": ["BL", "M12"]},
            {"01": ["BL", "M12"], "02": ["BL"]},
            {"01": ["BL"], "02": ["BL"], "03": ["BL"]},
            {"01": ["BL", "M12"], "03": ["M12"]},
        ),
        (
            {"PD01": ["BL", "M12"], "PD02": ["BL"]},
            {"PD01": ["BL", "M12"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL"], "PD02": ["BL"]},
        ),
    ],
)
@pytest.mark.parametrize("empty", [True, False])
def test_run_main_regenerate(
    workflow: TrackCurationWorkflow,
    participants_and_sessions_manifest: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_bidsified: dict[str, list[str]],
    empty: bool,
):
    workflow.empty = empty
    workflow.force = True

    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_downloaded=workflow.study.layout.dpath_pre_reorg,
        dpath_organized=workflow.study.layout.dpath_post_reorg,
        dpath_bidsified=workflow.study.layout.dpath_bids,
    )
    workflow.study.manifest = manifest

    # to be overwritten
    table_records = []
    for _, manifest_record in manifest.iterrows():
        participant_id = manifest_record[Manifest.col_participant_id]
        table_records.append(
            {
                CurationStatusTable.col_participant_id: participant_id,
                CurationStatusTable.col_visit_id: manifest_record[
                    Manifest.col_visit_id
                ],
                CurationStatusTable.col_session_id: manifest_record[
                    Manifest.col_session_id
                ],
                CurationStatusTable.col_datatype: manifest_record[
                    Manifest.col_datatype
                ],
                CurationStatusTable.col_participant_dicom_dir: participant_id,
                CurationStatusTable.col_in_pre_reorg: True,
                CurationStatusTable.col_in_post_reorg: True,
                CurationStatusTable.col_in_bids: True,
            }
        )
    table_old = CurationStatusTable(table_records)
    assert (
        table_old.save_with_backup(workflow.study.layout.fpath_curation_status)
        is not None
    )

    # regenerate the table
    workflow.run_main()
    table = CurationStatusTable.load(workflow.study.layout.fpath_curation_status)

    assert len(table) == len(manifest)
    check_curation_status_table(
        table=table,
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )


@pytest.mark.no_xdist
def test_run_cleanup(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    TrackCurationWorkflow(dpath_root=tmp_path).run_cleanup()
    assert (
        "Successfully generated/updated the dataset's curation status file"
        in caplog.text
    )
