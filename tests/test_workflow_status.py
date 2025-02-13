"""Tests for the dataset status workflow."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nipoppy.tabular.bagel import Bagel
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.tabular.manifest import Manifest
from nipoppy.workflows.dataset_status import StatusWorkflow

from .conftest import get_config


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


def make_doughnut(
    n_participants=10,
    session_ids=("BL", "M12"),
    n_success_percents=(80, 60, 40),
    randomize_counts=False,
) -> Doughnut:
    # reuse manifest generation
    manifest, session_participant_counts_df = make_manifest(
        n_participants, session_ids, randomize_counts
    )

    participant_ids = manifest["participant_id"].unique()

    # add pre_reorg, post_reorg, and bids status columns
    # always keep the first session as complete
    doughnut = manifest.copy()
    doughnut[
        [Doughnut.col_in_pre_reorg, Doughnut.col_in_post_reorg, Doughnut.col_in_bids]
    ] = False  # sets dtype to bool and avoids pandas warnings
    doughnut.loc[
        doughnut[Manifest.col_session_id] == session_ids[0], Doughnut.col_in_pre_reorg
    ] = True
    doughnut.loc[
        doughnut[Manifest.col_session_id] == session_ids[0], Doughnut.col_in_post_reorg
    ] = True
    doughnut.loc[
        doughnut[Manifest.col_session_id] == session_ids[0], Doughnut.col_in_bids
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

        doughnut.loc[
            doughnut[Manifest.col_session_id] == session_id, Doughnut.col_in_pre_reorg
        ] = [True] * n_success_pre_reorg + [False] * (
            n_session_participants - n_success_pre_reorg
        )
        doughnut.loc[
            doughnut[Manifest.col_session_id] == session_id, Doughnut.col_in_post_reorg
        ] = [True] * n_success_post_reorg + [False] * (
            n_session_participants - n_success_post_reorg
        )
        doughnut.loc[
            doughnut[Manifest.col_session_id] == session_id, Doughnut.col_in_bids
        ] = [True] * n_success_bids + [False] * (
            n_session_participants - n_success_bids
        )

    session_participant_counts_df = pd.DataFrame(
        data=zip(session_ids, participant_counts),
        columns=["session_id", "participant_count"],
    )

    return Doughnut(doughnut), session_participant_counts_df


def make_bagel(
    n_participants=10,
    session_ids=("BL", "M12"),
    n_success_percent=50,
    pipeline_configs=(
        ("dcm2bids", "1.0.0", "prepare"),
        ("dcm2bids", "1.0.0", "convert"),
        ("fmriprep", "1.0.0", "default"),
    ),
    randomize_counts=False,
) -> Bagel:

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
                Bagel.col_pipeline_name,
                Bagel.col_pipeline_version,
                Bagel.col_pipeline_step,
            ]
        ] = config
        _df_list.append(_df)

    bagel = Bagel(pd.concat(_df_list))

    # repeated participants for each pipeline config
    participant_counts = [n_configs * len(participant_ids)]

    # add pipeline status columns
    # always keep the first session as complete for all pipelines
    # except when testing 0% success
    if n_success_percent == 0:
        bagel[Bagel.col_status] = "FAIL"
    else:
        bagel[[Bagel.col_status]] = "INCOMPLETE"
        bagel.loc[
            bagel[Manifest.col_session_id] == session_ids[0], Bagel.col_status
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

            bagel.loc[
                bagel[Manifest.col_session_id] == session_id, Bagel.col_status
            ] = ["SUCCESS"] * n_success_pipeline + ["INCOMPLETE"] * (
                n_session_participants - n_success_pipeline
            )

    # participant_count column contains an int which is the sum of successful
    # rows across all processing pipelines for a given session
    session_participant_counts_df = pd.DataFrame(
        data=zip(session_ids, participant_counts),
        columns=["session_id", "participant_count"],
    )

    return bagel, session_participant_counts_df


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
        (100, ["BL", "M06", "M12", "M24"], (100, 80, 0), True),
    ],
)
def test_doughnut(
    dpath_root: Path,
    n_participants: int,
    session_ids: list,
    n_success_percents: tuple,
    randomize_counts: bool,
):

    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.doughnut, session_participant_counts_df = make_doughnut(
        n_participants=n_participants,
        session_ids=session_ids,
        n_success_percents=n_success_percents,
        randomize_counts=randomize_counts,
    )

    status_df = pd.DataFrame()
    status_df, _ = workflow._check_doughnut(status_df)

    status_df = pd.merge(
        status_df, session_participant_counts_df, on="session_id", how="left"
    )
    status_df["doughnut_counts"] = list(
        zip(
            status_df[Doughnut.col_in_pre_reorg],
            status_df[Doughnut.col_in_post_reorg],
            status_df[Doughnut.col_in_bids],
        )
    )

    # check manifest status
    assert set(status_df[Manifest.col_session_id].unique()) == set(session_ids)
    assert status_df["doughnut_counts"].equals(status_df["participant_count"])


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
def test_bagel(
    dpath_root: Path,
    n_participants: int,
    session_ids: list,
    n_success_percent: int,
    pipeline_configs: tuple,
    randomize_counts: bool,
):

    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.bagel, session_participant_counts_df = make_bagel(
        n_participants=n_participants,
        session_ids=session_ids,
        n_success_percent=n_success_percent,
        pipeline_configs=pipeline_configs,
        randomize_counts=randomize_counts,
    )

    status_df = pd.DataFrame()
    status_df, bagel_cols = workflow._check_bagel(status_df)

    if n_success_percent == 0:
        assert status_df.empty

    else:
        status_df = pd.merge(
            status_df, session_participant_counts_df, on="session_id", how="left"
        )

        # Sum up the bagel counts for all pipeline configs
        status_df["bagel_counts"] = 0
        for config in pipeline_configs:
            pipeline_status_col = f"{config[0]}\n{config[1]}\n{config[2]}"
            status_df["bagel_counts"] += status_df[pipeline_status_col]

        # check manifest status
        assert set(status_df[Manifest.col_session_id].unique()) == set(session_ids)
        assert status_df["bagel_counts"].equals(status_df["participant_count"])


@pytest.mark.parametrize("bagel", [pd.DataFrame(), make_bagel()[0]])
def test_run(dpath_root: Path, bagel: pd.DataFrame):
    workflow = StatusWorkflow(dpath_root=dpath_root)
    workflow.config = get_config()
    workflow.manifest = make_manifest(n_participants=10)[0]
    workflow.doughnut = pd.DataFrame()  # Checks for empty doughnut
    workflow.bagel = bagel
    status_df = workflow.run_main()

    assert status_df is not None
