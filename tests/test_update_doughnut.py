"""Tests for the update-doughnut workflow."""

from pathlib import Path

import pytest
from conftest import fake_dicoms_downloaded, fake_dicoms_organized
from fids.fids import create_fake_bids_dataset

from nipoppy.layout import DatasetLayout
from nipoppy.models.config import Config
from nipoppy.models.manifest import Manifest
from nipoppy.utils import save_json, strip_session
from nipoppy.workflows.update_doughnut import UpdateDoughnut


def _prepare_dataset(
    dpath_root: Path,
    participants_and_sessions_manifest: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_converted: dict[str, list[str]],
):
    # create the layout
    layout = DatasetLayout(dpath_root)

    # create the manifest
    data_manifest = []
    all_sessions = set()
    for participant in participants_and_sessions_manifest:
        for session in participants_and_sessions_manifest[participant]:
            data_manifest.append(
                {
                    Manifest.col_participant_id: participant,
                    Manifest.col_session: session,
                    Manifest.col_visit: session,
                    Manifest.col_datatype: [],
                }
            )
            all_sessions.add(session)
    manifest = Manifest(data_manifest)
    layout.fpath_manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(layout.fpath_manifest, index=False)

    config = Config(
        DATASET_NAME="test",
        DATASET_ROOT=dpath_root,
        CONTAINER_STORE=".",
        SESSIONS=sorted(list(all_sessions)),
        BIDS={},
        PROC_PIPELINES={},
    )
    save_json(config.model_dump(mode="json"), layout.fpath_config)

    # create fake downloaded DICOMs
    fake_dicoms_downloaded(
        dpath_root,
        participants_and_sessions_downloaded,
    )

    # create fake organized DICOMs
    fake_dicoms_organized(
        dpath_root,
        participants_and_sessions_organized,
    )

    # create fake BIDS dataset
    for participant, sessions in participants_and_sessions_converted.items():
        create_fake_bids_dataset(
            layout.dpath_bids,
            subjects=participant,
            sessions=[strip_session(session) for session in sessions],
        )

    return manifest


@pytest.mark.parametrize(
    (
        "participants_and_sessions_manifest,participants_and_sessions_downloaded"
        ",participants_and_sessions_organized,participants_and_sessions_converted"
    ),
    [
        (
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL", "ses-M12"]},
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL"]},
            {"01": ["ses-BL"], "02": ["ses-BL"]},
            {"01": ["ses-BL", "ses-M12"]},
        ),
        (
            {"01": ["ses-BL", "ses-M12"]},
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL", "ses-M12"]},
            {"01": ["ses-BL"], "02": ["ses-BL", "ses-M12"]},
            {"01": ["ses-BL"], "02": ["ses-BL"]},
        ),
    ],
)
@pytest.mark.parametrize("empty", [True, False])
def test_generate(
    participants_and_sessions_manifest: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_converted: dict[str, list[str]],
    empty: bool,
    tmp_path: Path,
):
    dpath_root = tmp_path / "my_dataset"

    workflow = UpdateDoughnut(dpath_root, empty=empty)

    manifest = _prepare_dataset(
        dpath_root,
        participants_and_sessions_manifest,
        participants_and_sessions_downloaded,
        participants_and_sessions_organized,
        participants_and_sessions_converted,
    )

    # the doughnut should have the same number of records as the manifest
    doughnut = workflow.generate_doughnut()
    assert len(doughnut) == len(manifest)

    if empty:
        for col in [
            doughnut.col_downloaded,
            doughnut.col_organized,
            doughnut.col_converted,
        ]:
            assert ~doughnut[col].all()
    else:
        for col, participants_and_sessions in {
            doughnut.col_downloaded: participants_and_sessions_downloaded,
            doughnut.col_organized: participants_and_sessions_organized,
            doughnut.col_converted: participants_and_sessions_converted,
        }.items():
            for participant in participants_and_sessions:
                for session in participants_and_sessions[participant]:
                    row = doughnut.loc[
                        (doughnut[doughnut.col_participant_id] == participant)
                        & (doughnut[doughnut.col_session] == session)
                    ]
                    try:
                        if session in participants_and_sessions_manifest[participant]:
                            assert row[col].all()
                        else:
                            assert len(row) == 0

                    except KeyError:
                        continue
