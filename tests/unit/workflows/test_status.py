"""Tests for the dataset status workflow."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.manifest import Manifest
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.workflows.dataset_status import StatusWorkflow
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


@pytest.mark.parametrize(
    "n_participants,session_ids,randomize_counts",
    [
        (10, ["BL", "M06", "M12", "M24"], False),
        (100, ["BL", "M06", "M12", "M24"], True),
    ],
)
def test_manifest(
    dpath_root: Path, n_participants: int, session_ids: list, randomize_counts: bool
):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.manifest, session_participant_counts_df = make_manifest(
        n_participants=n_participants,
        session_ids=session_ids,
        randomize_counts=randomize_counts,
    )

    status_df = pd.DataFrame()
    status_df = workflow._check_manifest(status_df)

    status_df = pd.merge(
        status_df, session_participant_counts_df, on="session_id", how="left"
    )

    # check manifest status
    assert set(status_df[Manifest.col_session_id].unique()) == set(session_ids)
    assert status_df["in_manifest"].equals(status_df["participant_count"])


@pytest.mark.parametrize(
    "n_participants,session_ids,n_success_percents,randomize_counts",
    [
        (10, ["BL", "M06", "M12", "M24"], (80, 60, 40), False),
        (10, ["BL", "M06", "M12", "M24"], (0, 0, 50), False),
        (10, ["BL", "M06", "M12", "M24"], (0, 100, 100), False),
        (10, ["BL", "M06", "M12", "M24"], (100, 0, 100), False),
        (100, ["BL", "M06", "M12", "M24"], (100, 80, 0), True),
    ],
)
def test_check_curation_status_table(
    dpath_root: Path,
    n_participants: int,
    session_ids: list,
    n_success_percents: tuple,
    randomize_counts: bool,
):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.curation_status_table, session_participant_counts_df = (
        make_curation_status_table(
            n_participants=n_participants,
            session_ids=session_ids,
            n_success_percents=n_success_percents,
            randomize_counts=randomize_counts,
        )
    )

    status_df = pd.DataFrame()
    status_df, _ = workflow._check_curation_status_table(status_df)

    status_df = pd.merge(
        status_df, session_participant_counts_df, on="session_id", how="left"
    )
    status_df["curation_counts"] = list(
        zip(
            status_df[CurationStatusTable.col_in_pre_reorg],
            status_df[CurationStatusTable.col_in_post_reorg],
            status_df[CurationStatusTable.col_in_bids],
        )
    )

    # check curation status
    assert set(status_df[Manifest.col_session_id].unique()) == set(session_ids)
    assert status_df["curation_counts"].equals(status_df["participant_count"])


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
    workflow.manifest = make_manifest(n_participants=10)[0]
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
    "n_participants,session_ids,n_success_percent,pipeline_configs,randomize_counts",
    [
        (
            10,
            ["BL", "M06"],
            0,
            (
                ("dcm2bids", "1.0.0", "prepare"),
                ("dcm2bids", "1.0.0", "convert"),
                ("fmriprep", "1.0.0", "default"),
            ),
            False,
        ),
        (
            10,
            ["BL", "M06", "M12", "M24"],
            50,
            (
                ("dcm2bids", "1.0.0", "prepare"),
                ("dcm2bids", "1.0.0", "convert"),
                ("fmriprep", "1.0.0", "default"),
            ),
            False,
        ),
        (
            100,
            ["BL", "M06", "M12", "M24"],
            100,
            (
                ("dcm2bids", "1.0.0", "prepare"),
                ("dcm2bids", "1.0.0", "convert"),
                ("fmriprep", "1.0.0", "default"),
            ),
            True,
        ),
    ],
)
def test_check_processing_status_table(
    dpath_root: Path,
    n_participants: int,
    session_ids: list,
    n_success_percent: int,
    pipeline_configs: tuple,
    randomize_counts: bool,
):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.processing_status_table, session_participant_counts_df = (
        make_processing_status_table(
            n_participants=n_participants,
            session_ids=session_ids,
            n_success_percent=n_success_percent,
            pipeline_configs=pipeline_configs,
            randomize_counts=randomize_counts,
        )
    )

    status_df = pd.DataFrame()
    status_df, _ = workflow._check_processing_status_table(status_df)

    if n_success_percent == 0:
        assert status_df.empty

    else:
        status_df = pd.merge(
            status_df, session_participant_counts_df, on="session_id", how="left"
        )

        # Sum up the counts for all pipeline configs
        status_df["processing_status_counts"] = 0
        for config in pipeline_configs:
            pipeline_status_col = f"{config[0]}\n{config[1]}\n{config[2]}"
            status_df["processing_status_counts"] += status_df[pipeline_status_col]

        # check processing status
        assert set(status_df[Manifest.col_session_id].unique()) == set(session_ids)
        assert status_df["processing_status_counts"].equals(
            status_df["participant_count"]
        )


@pytest.mark.parametrize(
    "processing_status_table",
    [ProcessingStatusTable(), make_processing_status_table()[0]],
)
def test_run(dpath_root: Path, processing_status_table: ProcessingStatusTable):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.study.config = get_config()
    workflow.manifest = make_manifest(n_participants=10)[0]
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
    workflow.manifest = make_manifest(n_participants=10)[0]
    workflow.curation_status_table = CurationStatusTable()  # Checks for empty table
    workflow.processing_status_table = processing_status_table
    status_df = workflow.run_main()

    assert status_df is not None
