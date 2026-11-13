"""Tests for the dataset status workflow."""

from pathlib import Path

import pandas as pd
import pytest

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.workflows.dataset_status import (
    CHECKPOINT_MANIFEST,
    COL_CHECKPOINT,
    LONG_STATUS_COLUMNS,
    StatusWorkflow,
)


@pytest.fixture()
def dpath_root(tmp_path: Path) -> Path:
    return tmp_path


def make_manifest(n_participants=10, session_ids=("BL", "M12")) -> Manifest:
    datatypes = ["anat", "dwi"]
    participant_ids = [str(i) for i in range(1, n_participants + 1)]

    return Manifest(
        pd.concat(
            [
                pd.DataFrame(
                    data={
                        Manifest.col_session_id: session_id,
                        Manifest.col_participant_id: participant_ids,
                        Manifest.col_visit_id: session_id,
                        Manifest.col_datatype: [datatypes for _ in participant_ids],
                    }
                )
                for session_id in session_ids
            ]
        )
    )


def make_mixed_datatype_status_tables():
    """Make a manifest and status tables with mixed datatypes."""
    manifest = Manifest(
        pd.DataFrame(
            [
                ("01", "BL", "BL", ["anat"]),
                ("02", "BL", "BL", ["anat", "dwi"]),
                ("03", "BL", "BL", ["dwi"]),
                ("01", "M12", "M12", ["anat"]),
                ("02", "M12", "M12", ["dwi"]),
                ("04", "M12", None, []),
            ],
            columns=[
                Manifest.col_participant_id,
                Manifest.col_visit_id,
                Manifest.col_session_id,
                Manifest.col_datatype,
            ],
        )
    )
    curation_columns = [
        CurationStatusTable.col_participant_id,
        CurationStatusTable.col_session_id,
        CurationStatusTable.col_in_pre_reorg,
        CurationStatusTable.col_in_post_reorg,
        CurationStatusTable.col_in_bids,
    ]
    curation_table = CurationStatusTable(
        pd.DataFrame(
            [
                ("01", "BL", True, True, True),
                ("02", "BL", False, False, False),
                ("03", "BL", True, True, True),
                ("01", "M12", True, True, False),
                ("02", "M12", False, False, False),
            ],
            columns=curation_columns,
        )
    )

    processing_table = ProcessingStatusTable(
        pd.DataFrame(
            [
                ("01", "BL", "pipeline", "1.0.0", "default", "SUCCESS"),
                ("02", "BL", "pipeline", "1.0.0", "default", "INCOMPLETE"),
                ("03", "BL", "pipeline", "1.0.0", "default", "SUCCESS"),
                ("01", "M12", "pipeline", "1.0.0", "default", "INCOMPLETE"),
                ("02", "M12", "pipeline", "1.0.0", "default", "INCOMPLETE"),
                ("orphan", "BL", "pipeline", "1.0.0", "default", "SUCCESS"),
                ("orphan", "ML12", "pipeline", "1.0.0", "default", "SUCCESS"),
            ],
            columns=[
                ProcessingStatusTable.col_participant_id,
                ProcessingStatusTable.col_session_id,
                ProcessingStatusTable.col_pipeline_name,
                ProcessingStatusTable.col_pipeline_version,
                ProcessingStatusTable.col_pipeline_step,
                ProcessingStatusTable.col_status,
            ],
        )
    )

    return manifest, curation_table, processing_table


@pytest.mark.parametrize(
    "datatype,expected",
    [
        (
            None,
            {
                "in_manifest": {"BL": 3, "M12": 2},
                "in_pre_reorg": {"BL": 2, "M12": 1},
                "in_post_reorg": {"BL": 2, "M12": 1},
                "in_bids": {"BL": 2, "M12": 0},
                "pipeline\n1.0.0\ndefault": {"BL": 2, "M12": 0},
            },
        ),
        (
            ("anat",),
            {
                "in_manifest": {"BL": 2, "M12": 1},
                "in_pre_reorg": {"BL": 1, "M12": 1},
                "in_post_reorg": {"BL": 1, "M12": 1},
                "in_bids": {"BL": 1, "M12": 0},
                "pipeline\n1.0.0\ndefault": {"BL": 1, "M12": 0},
            },
        ),
        (
            ("dwi",),
            {
                "in_manifest": {"BL": 2, "M12": 1},
                "in_pre_reorg": {"BL": 1, "M12": 0},
                "in_post_reorg": {"BL": 1, "M12": 0},
                "in_bids": {"BL": 1, "M12": 0},
                "pipeline\n1.0.0\ndefault": {"BL": 1, "M12": 0},
            },
        ),
        (
            ("anat", "dwi"),
            {
                "in_manifest": {"BL": 1},
                "in_pre_reorg": {"BL": 0},
                "in_post_reorg": {"BL": 0},
                "in_bids": {"BL": 0},
            },
        ),
    ],
)
def test_datatype_filters_all_status_tables(dpath_root: Path, datatype, expected):
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype=datatype)
    (
        workflow.study.manifest,
        workflow.curation_status_table,
        workflow.processing_status_table,
    ) = make_mixed_datatype_status_tables()

    assert workflow.run_main().to_dict() == expected


def test_filtering_hide_pipeline_without_success(
    dpath_root: Path, caplog: pytest.LogCaptureFixture
):
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype="anat")
    (
        workflow.study.manifest,
        workflow.curation_status_table,
        workflow.processing_status_table,
    ) = make_mixed_datatype_status_tables()
    workflow.processing_status_table.loc[
        workflow.processing_status_table[ProcessingStatusTable.col_pipeline_name]
        == "pipeline",
        ProcessingStatusTable.col_status,
    ] = "INCOMPLETE"

    status_df = workflow.run_main()

    assert status_df.index.tolist() == ["BL", "M12"]
    assert status_df.columns.tolist() == [
        CHECKPOINT_MANIFEST,
        *CurationStatusTable.status_cols,
    ]
    assert any(
        "no successful run was found in the imaging processing status file for pipeline(s): ['pipeline']"  # noqa: E501
        in record.message
        for record in caplog.records
    )


def test_unmatched_datatype_returns_none(
    dpath_root: Path,
    caplog: pytest.LogCaptureFixture,
):
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype=("fake",))
    (
        workflow.study.manifest,
        workflow.curation_status_table,
        workflow.processing_status_table,
    ) = make_mixed_datatype_status_tables()

    status_df = workflow.run_main()

    assert status_df is None
    assert any(
        "No imaging manifest rows matched datatype: {'fake'}" in r.message
        for r in caplog.records
    )


@pytest.mark.parametrize(
    "datatype,expected",
    [
        (("dwi", "anat"), {"anat", "dwi"}),
        ("dwi", {"dwi"}),
        (("fake",), {"fake"}),
        (None, None),
        ((), None),
    ],
)
def test_datatype_values_are_normalized(
    dpath_root: Path,
    datatype: tuple[str, ...] | str | None,
    expected: set[str] | None,
):
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype=datatype)

    assert workflow.datatypes == expected
    assert workflow.datatype == datatype


def test_str_with_datatype(dpath_root: Path):
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype=("anat",))

    assert "datatype" in str(workflow)


def test_empty_imaging_manifest_without_datatype(
    dpath_root: Path, caplog: pytest.LogCaptureFixture
):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.study.manifest = Manifest()
    workflow.curation_status_table = CurationStatusTable()
    workflow.processing_status_table = ProcessingStatusTable()

    assert workflow.run_main() is None
    assert "No imaging participant-session pairs found in the manifest." in (
        caplog.text
    )
    assert "matched datatype" not in caplog.text


def test_build_status_df(dpath_root: Path):
    """Completed records are copied into one universal long-form schema."""
    workflow = StatusWorkflow(dpath_root=dpath_root)
    (
        workflow.study.manifest,
        workflow.curation_status_table,
        workflow.processing_status_table,
    ) = make_mixed_datatype_status_tables()

    status_df = workflow._build_status_df()

    assert status_df.columns.tolist() == LONG_STATUS_COLUMNS
    assert status_df[COL_CHECKPOINT].value_counts().to_dict() == {
        CHECKPOINT_MANIFEST: 5,
        CurationStatusTable.col_in_pre_reorg: 3,
        CurationStatusTable.col_in_post_reorg: 3,
        CurationStatusTable.col_in_bids: 2,
        "pipeline\n1.0.0\ndefault": 2,
    }
    assert (
        status_df[Manifest.col_datatype]
        .apply(lambda value: isinstance(value, list))
        .all()
    )


def test_get_manifest_datatypes_with_empty_imaging_manifest():
    manifest_datatypes = StatusWorkflow._get_manifest_datatypes(pd.DataFrame())

    assert manifest_datatypes.empty
    assert manifest_datatypes.columns.tolist() == [
        *StatusWorkflow.index_cols,
        Manifest.col_datatype,
    ]


@pytest.mark.parametrize("empty_status,empty_manifest", [(True, False), (False, True)])
def test_attach_manifest_datatypes_with_empty_input(empty_status, empty_manifest):
    status_df = pd.DataFrame(
        [("01", "BL", CurationStatusTable.col_in_bids)],
        columns=[*StatusWorkflow.index_cols, COL_CHECKPOINT],
    )
    manifest_datatypes = pd.DataFrame(
        [("01", "BL", ["anat"])],
        columns=[*StatusWorkflow.index_cols, Manifest.col_datatype],
    )
    if empty_status:
        status_df = status_df.iloc[:0]
    if empty_manifest:
        manifest_datatypes = manifest_datatypes.iloc[:0]

    result = StatusWorkflow._attach_manifest_datatypes(status_df, manifest_datatypes)

    pd.testing.assert_frame_equal(result, pd.DataFrame(columns=LONG_STATUS_COLUMNS))


def test_build_status_df_with_no_imaging_sessions(dpath_root: Path):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.study.manifest = Manifest(
        pd.DataFrame(
            [("01", "V1", None, None)],
            columns=[
                Manifest.col_participant_id,
                Manifest.col_visit_id,
                Manifest.col_session_id,
                Manifest.col_datatype,
            ],
        )
    )
    workflow.curation_status_table = CurationStatusTable()
    workflow.processing_status_table = ProcessingStatusTable()

    status_df = workflow._build_status_df()

    assert status_df.empty
    assert status_df.columns.tolist() == LONG_STATUS_COLUMNS


def test_build_status_df_does_not_mutate_source_tables(dpath_root: Path):
    """Ensure that the original tables are not modified by the workflow."""
    workflow = StatusWorkflow(dpath_root=dpath_root)
    (
        workflow.study.manifest,
        workflow.curation_status_table,
        workflow.processing_status_table,
    ) = make_mixed_datatype_status_tables()
    manifest = workflow.study.manifest.copy(deep=True)
    curation_status_table = workflow.curation_status_table.copy(deep=True)
    processing_status_table = workflow.processing_status_table.copy(deep=True)

    workflow._build_status_df()

    pd.testing.assert_frame_equal(workflow.study.manifest, manifest)
    pd.testing.assert_frame_equal(workflow.curation_status_table, curation_status_table)
    pd.testing.assert_frame_equal(
        workflow.processing_status_table, processing_status_table
    )


def test_filter_uses_manifest_datatypes(dpath_root: Path):
    """Status rows and the manifest use combined participant-session datatypes."""
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype=("anat", "dwi"))
    workflow.study.manifest = Manifest(
        pd.DataFrame(
            [
                ("01", "V1", "BL", ["anat"]),
                ("01", "V2", "BL", ["dwi"]),
            ],
            columns=[
                Manifest.col_participant_id,
                Manifest.col_visit_id,
                Manifest.col_session_id,
                Manifest.col_datatype,
            ],
        )
    )
    workflow.curation_status_table = CurationStatusTable(
        pd.DataFrame(
            [("01", "BL", True, True, True)],
            columns=[
                CurationStatusTable.col_participant_id,
                CurationStatusTable.col_session_id,
                *CurationStatusTable.status_cols,
            ],
        )
    )
    workflow.processing_status_table = ProcessingStatusTable(
        pd.DataFrame(
            [("01", "BL", "pipeline", "1.0.0", "default", "SUCCESS")],
            columns=[
                ProcessingStatusTable.col_participant_id,
                ProcessingStatusTable.col_session_id,
                ProcessingStatusTable.col_pipeline_name,
                ProcessingStatusTable.col_pipeline_version,
                ProcessingStatusTable.col_pipeline_step,
                ProcessingStatusTable.col_status,
            ],
        )
    )

    status_df = StatusWorkflow._filter_status_df(
        workflow._build_status_df(), datatypes=workflow.datatypes
    )

    # Both datatypes are present across visits for the same session.
    assert status_df[COL_CHECKPOINT].value_counts().to_dict() == {
        CurationStatusTable.col_in_pre_reorg: 1,
        CurationStatusTable.col_in_post_reorg: 1,
        CurationStatusTable.col_in_bids: 1,
        CHECKPOINT_MANIFEST: 1,
        "pipeline\n1.0.0\ndefault": 1,
    }
    assert status_df.loc[
        status_df[COL_CHECKPOINT] == CHECKPOINT_MANIFEST,
        Manifest.col_datatype,
    ].tolist() == [["anat", "dwi"]]


def test_multivisit_participant_sessions_count_once_for_bids_completion(
    dpath_root: Path,
):
    """Multiple visit rows for one session count as one participant-session."""
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.study.manifest = Manifest(
        pd.DataFrame(
            [
                ("01", "V1", "BL", ["anat"]),
                ("01", "V2", "BL", ["dwi"]),
                ("02", "V1", "BL", ["anat"]),
                ("02", "V2", "BL", ["dwi"]),
            ],
            columns=[
                Manifest.col_participant_id,
                Manifest.col_visit_id,
                Manifest.col_session_id,
                Manifest.col_datatype,
            ],
        )
    )
    workflow.curation_status_table = CurationStatusTable(
        pd.DataFrame(
            [
                ("01", "BL", True, True, True),
                ("02", "BL", True, True, True),
            ],
            columns=[
                CurationStatusTable.col_participant_id,
                CurationStatusTable.col_session_id,
                *CurationStatusTable.status_cols,
            ],
        )
    )
    workflow.processing_status_table = ProcessingStatusTable()

    long_status_df = workflow._build_status_df()
    assert long_status_df.loc[
        long_status_df[COL_CHECKPOINT] == CHECKPOINT_MANIFEST,
        Manifest.col_datatype,
    ].tolist() == [["anat", "dwi"], ["anat", "dwi"]]

    status_df = workflow.run_main()

    assert status_df.loc["BL", CHECKPOINT_MANIFEST] == 2
    assert status_df.loc["BL", CurationStatusTable.col_in_bids] == 2
    assert CurationStatusTable.col_in_pre_reorg not in status_df.columns
    assert CurationStatusTable.col_in_post_reorg not in status_df.columns


def test_datatype_filter_bids_completion_drops_curation_stages(
    dpath_root: Path,
):
    """When BIDS count equals manifest count under datatype filter, hide pre/post reorg."""
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype="dwi")
    workflow.study.manifest = make_manifest(n_participants=1, session_ids=["BL"])
    workflow.curation_status_table = CurationStatusTable(
        pd.DataFrame(
            [("1", "BL", True, True, True)],
            columns=[
                CurationStatusTable.col_participant_id,
                CurationStatusTable.col_session_id,
                *CurationStatusTable.status_cols,
            ],
        )
    )
    workflow.processing_status_table = ProcessingStatusTable()

    status_df = workflow.run_main()

    assert status_df.columns.tolist() == [
        CHECKPOINT_MANIFEST,
        CurationStatusTable.col_in_bids,
    ]


def test_empty_processing_table_has_only_missing_file_warning(
    dpath_root: Path,
    caplog: pytest.LogCaptureFixture,
):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.study.manifest = make_manifest(n_participants=1)
    workflow.curation_status_table = CurationStatusTable()
    workflow.processing_status_table = ProcessingStatusTable()

    workflow.run_main()

    assert any(
        "No imaging processing status file found" in record.message
        for record in caplog.records
    )
    assert not any(
        "no successful run was found" in record.message for record in caplog.records
    )
