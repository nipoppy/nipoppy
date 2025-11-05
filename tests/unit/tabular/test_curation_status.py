"""Tests for the curation status file."""

from contextlib import nullcontext
from pathlib import Path

import pandas as pd
import pytest

from nipoppy.env import FAKE_SESSION_ID, StrOrPathLike
from nipoppy.exceptions import WorkflowError
from nipoppy.tabular.curation_status import (
    CurationStatusTable,
    generate_curation_status_table,
    update_curation_status_table,
)
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from tests.conftest import DPATH_TEST_DATA, check_curation_status_table, prepare_dataset


@pytest.fixture
def data():
    return {
        CurationStatusTable.col_participant_id: ["01", "01", "02", "02"],
        CurationStatusTable.col_visit_id: ["BL", "M12", "BL", "M12"],
        CurationStatusTable.col_session_id: ["BL", "M12", "BL", "M12"],
        CurationStatusTable.col_datatype: ["anat", "anat", "anat", "anat"],
        CurationStatusTable.col_participant_dicom_dir: ["01", "01", "02", "02"],
        CurationStatusTable.col_in_pre_reorg: [True, True, True, False],
        CurationStatusTable.col_in_post_reorg: [True, False, True, False],
        CurationStatusTable.col_in_bids: [True, False, False, False],
    }


@pytest.mark.parametrize(
    "fpath",
    [
        DPATH_TEST_DATA / "curation_status1.tsv",
        DPATH_TEST_DATA / "curation_status2.tsv",
    ],
)
@pytest.mark.parametrize("validate", [True, False])
def test_load(fpath, validate):
    assert isinstance(
        CurationStatusTable.load(fpath, validate=validate), CurationStatusTable
    )


@pytest.mark.parametrize(
    "fpath,is_valid",
    [
        (DPATH_TEST_DATA / "curation_status1.tsv", True),
        (DPATH_TEST_DATA / "curation_status2.tsv", True),
        (DPATH_TEST_DATA / "curation_status_invalid1.tsv", False),
        (DPATH_TEST_DATA / "curation_status_invalid2.tsv", False),
    ],
)
def test_validate(fpath, is_valid):
    table = CurationStatusTable.load(fpath, validate=False)
    with pytest.raises(WorkflowError) if not is_valid else nullcontext():
        assert isinstance(CurationStatusTable.validate(table), CurationStatusTable)


@pytest.mark.parametrize(
    "col",
    [
        CurationStatusTable.col_in_pre_reorg,
        CurationStatusTable.col_in_post_reorg,
        CurationStatusTable.col_in_bids,
    ],
)
def test_check_status_col(col):
    assert CurationStatusTable._check_status_col(col) == col


def test_check_status_col_invalid():
    with pytest.raises(WorkflowError, match="Invalid status column"):
        CurationStatusTable._check_status_col("invalid_col")


@pytest.mark.parametrize("value", [True, False])
def test_check_status_value(value):
    assert CurationStatusTable._check_status_value(value) == value


def test_check_status_value_invalid():
    with pytest.raises(WorkflowError, match="Invalid status value"):
        assert CurationStatusTable._check_status_value("123")


@pytest.mark.parametrize(
    "participant_id,session_id,col,expected_status",
    [
        ("01", "BL", CurationStatusTable.col_in_pre_reorg, True),
        ("01", "BL", CurationStatusTable.col_in_post_reorg, True),
        ("01", "BL", CurationStatusTable.col_in_bids, True),
        ("02", "M12", CurationStatusTable.col_in_pre_reorg, False),
        ("02", "M12", CurationStatusTable.col_in_post_reorg, False),
        ("02", "M12", CurationStatusTable.col_in_bids, False),
    ],
)
def test_get_status(data, participant_id, session_id, col, expected_status):
    assert (
        CurationStatusTable(data).get_status(participant_id, session_id, col)
        == expected_status
    )


@pytest.mark.parametrize(
    "participant_id,session_id,col,status",
    [
        ("01", "BL", CurationStatusTable.col_in_pre_reorg, False),
        ("01", "BL", CurationStatusTable.col_in_post_reorg, False),
        ("01", "BL", CurationStatusTable.col_in_bids, False),
        ("02", "M12", CurationStatusTable.col_in_pre_reorg, True),
        ("02", "M12", CurationStatusTable.col_in_post_reorg, True),
        ("02", "M12", CurationStatusTable.col_in_bids, True),
    ],
)
def test_set_status(data, participant_id, session_id, col, status):
    table = CurationStatusTable(data)
    table.set_status(
        participant_id=participant_id, session_id=session_id, col=col, status=status
    )
    assert (
        table.get_status(participant_id=participant_id, session_id=session_id, col=col)
        == status
    )


def test_set_status_index_reset(data):
    table = CurationStatusTable(data)
    with pytest.raises(WorkflowError):
        table.set_status("01", "BL", "bad_col", True)

    assert set(table.columns) == set(CurationStatusTable().columns)
    assert isinstance(table.index, pd.RangeIndex)


@pytest.mark.parametrize(
    "status_col,participant_id,session_id,expected_count",
    [
        (CurationStatusTable.col_in_pre_reorg, None, None, 3),
        (CurationStatusTable.col_in_post_reorg, None, None, 2),
        (CurationStatusTable.col_in_bids, None, None, 1),
        (CurationStatusTable.col_in_pre_reorg, "01", None, 2),
        (CurationStatusTable.col_in_post_reorg, None, "M12", 0),
        (CurationStatusTable.col_in_bids, "01", "BL", 1),
    ],
)
def test_get_participant_sessions_helper(
    data, status_col, participant_id, session_id, expected_count
):
    table = CurationStatusTable(data)
    count = 0
    for _ in table._get_participant_sessions_helper(
        status_col=status_col, participant_id=participant_id, session_id=session_id
    ):
        count += 1
    assert count == expected_count


@pytest.mark.parametrize(
    (
        "participants_and_sessions_manifest1"
        ",participants_and_sessions_manifest2"
        ",participants_and_sessions_downloaded"
        ",participants_and_sessions_organized"
        ",participants_and_sessions_bidsified"
        ",dpath_downloaded_relative"
        ",dpath_organized_relative"
        ",dpath_bidsified_relative"
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
            "downloaded",
            "organized",
            "bidsified",
        ),
        (
            {"PD01": ["BL"], "PD02": ["BL"]},
            {"PD01": ["BL", "M12"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL", "M12"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL"], "PD02": ["BL", "M12"]},
            {"PD01": ["BL"], "PD02": ["BL"]},
            Path("scratch", "raw_dicom"),
            Path("dicom"),
            Path("bids"),
        ),
    ],
)
@pytest.mark.parametrize("empty", [True, False])
@pytest.mark.parametrize("str_paths", [False, True])
def test_generate_and_update(
    participants_and_sessions_manifest1: dict[str, list[str]],
    participants_and_sessions_manifest2: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_bidsified: dict[str, list[str]],
    dpath_downloaded_relative: StrOrPathLike,
    dpath_organized_relative: StrOrPathLike,
    dpath_bidsified_relative: StrOrPathLike,
    empty: bool,
    str_paths: bool,
    tmp_path: Path,
):
    dpath_root = tmp_path / "my_dataset"
    dpath_downloaded = dpath_root / dpath_downloaded_relative
    dpath_organized = dpath_root / dpath_organized_relative
    dpath_bidsified = dpath_root / dpath_bidsified_relative

    if str_paths:
        dpath_downloaded = str(dpath_downloaded)
        dpath_organized = str(dpath_organized)
        dpath_bidsified = str(dpath_bidsified)

    # create the manifest
    manifest1 = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_bidsified=dpath_bidsified,
    )

    # generate the curation status table
    table1 = generate_curation_status_table(
        manifest=manifest1,
        dicom_dir_map=DicomDirMap.load_or_generate(
            manifest=manifest1, fpath_dicom_dir_map=None, participant_first=True
        ),
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_bidsified=dpath_bidsified,
        empty=empty,
    )
    # the table should have the same number of records as the manifest
    assert len(table1) == len(manifest1)

    check_curation_status_table(
        table=table1,
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )

    # create a new manifest
    manifest2 = prepare_dataset(participants_and_sessions_manifest2)
    table2 = update_curation_status_table(
        curation_status_table=table1,
        manifest=manifest2,
        dicom_dir_map=DicomDirMap.load_or_generate(
            manifest=manifest2, fpath_dicom_dir_map=None, participant_first=True
        ),
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_bidsified=dpath_bidsified,
        empty=empty,
    )
    assert len(table2) == len(manifest2)

    check_curation_status_table(
        table=table2,
        participants_and_sessions_manifest=participants_and_sessions_manifest2,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )


def test_generate_missing_paths(tmp_path: Path):
    participants_and_sessions = {
        "01": ["BL", "M12"],
        "02": ["BL", "M12"],
    }

    dpath_root = tmp_path / "my_dataset"
    dpath_downloaded = dpath_root / "downloaded"
    dpath_organized = None
    dpath_bidsified = dpath_root / "bids"

    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_downloaded=participants_and_sessions,
        participants_and_sessions_organized=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_bidsified=dpath_bidsified,
    )

    table = generate_curation_status_table(
        manifest=manifest,
        dicom_dir_map=DicomDirMap.load_or_generate(
            manifest=manifest, fpath_dicom_dir_map=None, participant_first=True
        ),
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_bidsified=dpath_bidsified,
        empty=False,
    )

    assert table[CurationStatusTable.col_in_pre_reorg].all()
    assert (~table[CurationStatusTable.col_in_post_reorg]).all()
    assert table[CurationStatusTable.col_in_bids].all()


def test_curation_status_table_generation_no_session(
    tmp_path: Path,
):
    """Test curation status table generation when there are no session folders.

    Check that the subjects are included and bids valid in the table.
    """
    participants_and_sessions_manifest = {
        "01": [FAKE_SESSION_ID],
        "02": [FAKE_SESSION_ID],
    }
    participants_and_sessions_bidsified = {
        "01": [None],
        "02": [None],
    }

    dpath_root = tmp_path / "my_dataset"
    dpath_bidsified = dpath_root / "bids"

    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=None,
        participants_and_sessions_organized=None,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_downloaded=None,
        dpath_organized=None,
        dpath_bidsified=dpath_bidsified,
    )

    table = generate_curation_status_table(
        manifest=manifest,
        dicom_dir_map=DicomDirMap.load_or_generate(
            manifest=manifest, fpath_dicom_dir_map=None, participant_first=True
        ),
        dpath_downloaded=None,
        dpath_organized=None,
        dpath_bidsified=dpath_bidsified,
        empty=False,
    )

    assert table[CurationStatusTable.col_participant_id].to_list() == ["01", "02"]
    assert table[CurationStatusTable.col_in_bids].all()
