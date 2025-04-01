"""Tests for the TrackCurationWorkflow."""

from pathlib import Path

import pytest

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import save_json
from nipoppy.workflows.track_curation import TrackCurationWorkflow

from .conftest import (
    ATTR_TO_DPATH_MAP,
    ATTR_TO_FPATH_MAP,
    check_curation_status_table,
    create_empty_dataset,
    get_config,
    prepare_dataset,
)


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
    participants_and_sessions_manifest1: dict[str, list[str]],
    participants_and_sessions_manifest2: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_bidsified: dict[str, list[str]],
    empty: bool,
    tmp_path: Path,
):
    dpath_root = tmp_path / "my_dataset"

    dpath_downloaded = dpath_root / ATTR_TO_DPATH_MAP["dpath_pre_reorg"]
    dpath_organized = dpath_root / ATTR_TO_DPATH_MAP["dpath_post_reorg"]
    dpath_bidsified = dpath_root / ATTR_TO_DPATH_MAP["dpath_bids"]
    fpath_manifest = dpath_root / ATTR_TO_FPATH_MAP["fpath_manifest"]
    fpath_config = dpath_root / ATTR_TO_FPATH_MAP["fpath_config"]
    fpath_table = dpath_root / ATTR_TO_FPATH_MAP["fpath_curation_status"]

    create_empty_dataset(dpath_root)
    manifest1 = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_bidsified=dpath_bidsified,
    )
    manifest1.save_with_backup(fpath_manifest)

    # prepare config file
    config = get_config(
        visit_ids=list(manifest1[Manifest.col_visit_id].unique()),
    )
    save_json(config.model_dump(mode="json"), fpath_config)

    # generate the curation status table
    TrackCurationWorkflow(dpath_root=dpath_root, empty=empty).run_main()
    table1 = CurationStatusTable.load(fpath_table)

    assert len(table1) == len(manifest1)
    check_curation_status_table(
        table=table1,
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )

    # update the manifest
    manifest2 = prepare_dataset(participants_and_sessions_manifest2)
    manifest2.save_with_backup(fpath_manifest)

    # update the curation status table
    TrackCurationWorkflow(dpath_root=dpath_root, empty=empty).run()
    table2 = CurationStatusTable.load(fpath_table)

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
    participants_and_sessions_manifest: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_bidsified: dict[str, list[str]],
    empty: bool,
    tmp_path: Path,
):
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)

    dpath_downloaded = dpath_root / ATTR_TO_DPATH_MAP["dpath_pre_reorg"]
    dpath_organized = dpath_root / ATTR_TO_DPATH_MAP["dpath_post_reorg"]
    dpath_bidsified = dpath_root / ATTR_TO_DPATH_MAP["dpath_bids"]
    fpath_manifest = dpath_root / ATTR_TO_FPATH_MAP["fpath_manifest"]
    fpath_config = dpath_root / ATTR_TO_FPATH_MAP["fpath_config"]
    fpath_table = dpath_root / ATTR_TO_FPATH_MAP["fpath_curation_status"]

    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_bidsified=dpath_bidsified,
    )
    manifest.save_with_backup(fpath_manifest)

    # prepare config file
    config = get_config(
        visit_ids=list(manifest[Manifest.col_visit_id].unique()),
    )
    save_json(config.model_dump(mode="json"), fpath_config)

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
    assert table_old.save_with_backup(fpath_table) is not None

    # regenerate the table
    TrackCurationWorkflow(
        dpath_root=dpath_root, empty=empty, regenerate=True
    ).run_main()
    table = CurationStatusTable.load(fpath_table)

    assert len(table) == len(manifest)
    check_curation_status_table(
        table=table,
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )


def test_run_cleanup(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    TrackCurationWorkflow(dpath_root=tmp_path).run_cleanup()
    assert (
        "Successfully generated/updated the dataset's curation status file!"
        in caplog.text
    )
