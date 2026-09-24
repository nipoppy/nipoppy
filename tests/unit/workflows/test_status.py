"""Tests for the dataset status workflow."""

from pathlib import Path

import numpy as np
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
from tests.conftest import get_config


@pytest.fixture()
def dpath_root(tmp_path: Path) -> Path:
    return tmp_path


def make_manifest(
    n_participants=10, session_ids=("BL", "M12"), randomize_counts=False
) -> Manifest:
    datatypes = ["anat", "dwi"]

    participant_ids = [str(i) for i in range(1, n_participants + 1)]

    # generate participants per session (potentially randomizing the number of participants)
    _df = pd.DataFrame(
        data={
            Manifest.col_session_id: session_ids[0],
            Manifest.col_participant_id: participant_ids,
            Manifest.col_visit_id: session_ids[0],
            Manifest.col_datatype: [datatypes for _ in range(n_participants)],
        }
    )

    _df_list = [_df]
    participant_counts = [len(participant_ids)]

    for session_id in session_ids[1:]:
        if randomize_counts:
            participant_count_for_session = np.random.randint(1, n_participants + 1)
        else:
            participant_count_for_session = n_participants

        _df = pd.DataFrame(
            data={
                Manifest.col_session_id: session_id,
                Manifest.col_participant_id: participant_ids[
                    :participant_count_for_session
                ],
                Manifest.col_visit_id: session_id,
                Manifest.col_datatype: [
                    datatypes for _ in range(participant_count_for_session)
                ],
            }
        )

        _df_list.append(_df)
        participant_counts.append(participant_count_for_session)

    _df = Manifest(pd.concat(_df_list))

    session_participant_counts_df = pd.DataFrame(
        data=zip(session_ids, participant_counts),
        columns=[Manifest.col_session_id, "participant_count"],
    )

    return _df, session_participant_counts_df


def make_curation_status_table(
    n_participants=10,
    session_ids=("BL", "M12"),
    n_success_percents=(80, 60, 40),
    randomize_counts=False,
    from_bids=False,
) -> CurationStatusTable:
    # reuse manifest generation
    manifest, session_participant_counts_df = make_manifest(
        n_participants, session_ids, randomize_counts
    )

    participant_ids = manifest["participant_id"].unique()

    # add pre_reorg, post_reorg, and bids status columns
    # always keep the first session as complete
    table = manifest.copy()
    table[
        [
            CurationStatusTable.col_in_pre_reorg,
            CurationStatusTable.col_in_post_reorg,
            CurationStatusTable.col_in_bids,
        ]
    ] = False  # sets dtype to bool and avoids pandas warnings

    table.loc[
        table[Manifest.col_session_id] == session_ids[0],
        CurationStatusTable.col_in_bids,
    ] = True

    if from_bids:
        # participant_counts contains a tuple of (pre_reorg, post_reorg, bids)
        participant_counts = [(0, 0, len(participant_ids))]
    else:
        table.loc[
            table[Manifest.col_session_id] == session_ids[0],
            CurationStatusTable.col_in_pre_reorg,
        ] = True
        table.loc[
            table[Manifest.col_session_id] == session_ids[0],
            CurationStatusTable.col_in_post_reorg,
        ] = True

        # participant_counts contains a tuple of (pre_reorg, post_reorg, bids)
        participant_counts = [
            (len(participant_ids), len(participant_ids), len(participant_ids))
        ]

    # add the rest of the sessions
    for session_id in session_ids[1:]:
        n_session_participants = session_participant_counts_df[
            session_participant_counts_df[Manifest.col_session_id] == session_id
        ]["participant_count"].values[0]
        n_success_pre_reorg = int(n_session_participants * n_success_percents[0] / 100)
        n_success_post_reorg = int(n_session_participants * n_success_percents[1] / 100)
        n_success_bids = int(n_session_participants * n_success_percents[2] / 100)
        participant_counts.append(
            (n_success_pre_reorg, n_success_post_reorg, n_success_bids)
        )

        table.loc[
            table[Manifest.col_session_id] == session_id,
            CurationStatusTable.col_in_pre_reorg,
        ] = [True] * n_success_pre_reorg + [False] * (
            n_session_participants - n_success_pre_reorg
        )
        table.loc[
            table[Manifest.col_session_id] == session_id,
            CurationStatusTable.col_in_post_reorg,
        ] = [True] * n_success_post_reorg + [False] * (
            n_session_participants - n_success_post_reorg
        )
        table.loc[
            table[Manifest.col_session_id] == session_id,
            CurationStatusTable.col_in_bids,
        ] = [True] * n_success_bids + [False] * (
            n_session_participants - n_success_bids
        )

    session_participant_counts_df = pd.DataFrame(
        data=zip(session_ids, participant_counts),
        columns=["session_id", "participant_count"],
    )

    return CurationStatusTable(table), session_participant_counts_df


def make_processing_status_table(
    n_participants=10,
    session_ids=("BL", "M12"),
    n_success_percent=50,
    pipeline_configs=(
        ("dcm2bids", "1.0.0", "prepare"),
        ("dcm2bids", "1.0.0", "convert"),
        ("fmriprep", "1.0.0", "default"),
    ),
    randomize_counts=False,
) -> ProcessingStatusTable:
    manifest, session_participant_counts_df = make_manifest(
        n_participants, session_ids, randomize_counts
    )

    participant_ids = manifest["participant_id"].unique()
    n_configs = len(pipeline_configs)
    # add pipeline columns
    _df_list = []
    for config in pipeline_configs:
        _df = manifest.copy()
        _df[
            [
                ProcessingStatusTable.col_pipeline_name,
                ProcessingStatusTable.col_pipeline_version,
                ProcessingStatusTable.col_pipeline_step,
            ]
        ] = config
        _df_list.append(_df)

    table = ProcessingStatusTable(pd.concat(_df_list))

    # repeated participants for each pipeline config
    participant_counts = [n_configs * len(participant_ids)]

    # add pipeline status columns
    # always keep the first session as complete for all pipelines
    # except when testing 0% success
    if n_success_percent == 0:
        table[ProcessingStatusTable.col_status] = "FAIL"
    else:
        table[[ProcessingStatusTable.col_status]] = "INCOMPLETE"
        table.loc[
            table[Manifest.col_session_id] == session_ids[0],
            ProcessingStatusTable.col_status,
        ] = "SUCCESS"

        # add the rest of the sessions
        for session_id in session_ids[1:]:
            n_session_participants = (
                n_configs
                * session_participant_counts_df[
                    session_participant_counts_df[Manifest.col_session_id] == session_id
                ]["participant_count"].values[0]
            )
            n_success_pipeline = int(n_session_participants * n_success_percent / 100)
            participant_counts.append(n_success_pipeline)

            table.loc[
                table[Manifest.col_session_id] == session_id,
                ProcessingStatusTable.col_status,
            ] = ["SUCCESS"] * n_success_pipeline + ["INCOMPLETE"] * (
                n_session_participants - n_success_pipeline
            )

    # participant_count column contains an int which is the sum of successful
    # rows across all processing pipelines for a given session
    session_participant_counts_df = pd.DataFrame(
        data=zip(session_ids, participant_counts),
        columns=["session_id", "participant_count"],
    )

    return table, session_participant_counts_df


def make_mixed_datatype_status_tables():
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
    curation_status_table = CurationStatusTable(
        pd.DataFrame(
            [
                ("01", "BL", True, True, True),
                ("02", "BL", False, False, False),
                ("03", "BL", True, True, True),
                ("01", "M12", True, True, False),
                ("02", "M12", False, False, False),
            ],
            columns=[
                CurationStatusTable.col_participant_id,
                CurationStatusTable.col_session_id,
                CurationStatusTable.col_in_pre_reorg,
                CurationStatusTable.col_in_post_reorg,
                CurationStatusTable.col_in_bids,
            ],
        )
    )

    processing_status_table = ProcessingStatusTable(
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

    return manifest, curation_status_table, processing_status_table


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


def test_unmatched_datatype_returns_empty_table(
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
        ((" dwi ", "anat "), {"anat", "dwi"}),
        (("fake",), {"fake"}),
        (("", " "), None),
    ],
)
def test_datatype_values_are_normalized(
    dpath_root: Path, datatype: tuple[str, ...], expected: set[str] | None
):
    workflow = StatusWorkflow(dpath_root=dpath_root, datatype=datatype)

    assert workflow.datatypes == expected


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
        *StatusWorkflow.INDEX_COLS,
        Manifest.col_datatype,
    ]


@pytest.mark.parametrize("empty_status,empty_manifest", [(True, False), (False, True)])
def test_attach_manifest_datatypes_with_empty_input(empty_status, empty_manifest):
    status_df = pd.DataFrame(
        [("01", "BL", CurationStatusTable.col_in_bids)],
        columns=[*StatusWorkflow.INDEX_COLS, COL_CHECKPOINT],
    )
    manifest_datatypes = pd.DataFrame(
        [("01", "BL", ["anat"])],
        columns=[*StatusWorkflow.INDEX_COLS, Manifest.col_datatype],
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

    status_df = workflow._filter_status_df(workflow._build_status_df())

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
    workflow.study.manifest = make_manifest(n_participants=1, session_ids=["BL"])[0]
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
    workflow.study.manifest = make_manifest(n_participants=1)[0]
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


# Check col_in_pre_reorg and col_in_post_reorg are not shown when all values are False
@pytest.mark.parametrize(
    "n_participants,session_ids,n_success_percents,randomize_counts",
    [
        (10, ["BL", "M12"], (0, 0, 100), False),
    ],
)
def test_check_curation_status_table_from_bids_init(
    dpath_root: Path,
    n_participants: int,
    session_ids: list,
    n_success_percents: tuple,
    randomize_counts: bool,
):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.study.manifest = make_manifest(n_participants=10)[0]
    workflow.curation_status_table, session_participant_counts_df = (
        make_curation_status_table(
            n_participants=n_participants,
            session_ids=session_ids,
            n_success_percents=n_success_percents,
            randomize_counts=randomize_counts,
            from_bids=True,  # Simulate BIDS initialization
        )
    )

    status_df = workflow.run_main()

    # Check that col_in_pre_reorg and col_in_post_reorg are not in the status_df
    assert CurationStatusTable.col_in_pre_reorg not in status_df.columns
    assert CurationStatusTable.col_in_post_reorg not in status_df.columns
    assert CurationStatusTable.col_in_bids in status_df.columns


@pytest.mark.parametrize(
    "processing_status_table",
    [ProcessingStatusTable(), make_processing_status_table()[0]],
)
def test_run(dpath_root: Path, processing_status_table: ProcessingStatusTable):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.study.config = get_config()
    workflow.study.manifest = make_manifest(n_participants=10)[0]
    workflow.curation_status_table = CurationStatusTable()  # Checks for empty table
    workflow.processing_status_table = processing_status_table
    status_df = workflow.run_main()

    assert status_df is not None


@pytest.mark.parametrize(
    "processing_status_table",
    [ProcessingStatusTable(), make_processing_status_table()[0]],
)
def test_run_sub_directory(
    dpath_root: Path, processing_status_table: ProcessingStatusTable
):
    derivatives = dpath_root.joinpath("derivatives")
    derivatives.mkdir(parents=True, exist_ok=True)

    workflow = StatusWorkflow(dpath_root=derivatives)
    workflow.study.config = get_config()
    workflow.study.manifest = make_manifest(n_participants=10)[0]
    workflow.curation_status_table = CurationStatusTable()  # Checks for empty table
    workflow.processing_status_table = processing_status_table
    status_df = workflow.run_main()

    assert status_df is not None
