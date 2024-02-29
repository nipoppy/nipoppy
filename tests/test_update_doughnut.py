"""Tests for the update-doughnut workflow."""

from pathlib import Path
from typing import Optional

import pandas as pd
import pytest
from conftest import (
    ATTR_TO_DPATH_MAP,
    ATTR_TO_FPATH_MAP,
    fake_dicoms_downloaded,
    fake_dicoms_organized,
)
from fids.fids import create_fake_bids_dataset

from nipoppy.config import Config
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import save_json, strip_session
from nipoppy.workflows.doughnut import (
    DoughnutWorkflow,
    generate_doughnut,
    update_doughnut,
)


def _prepare_dataset(
    participants_and_sessions_manifest: dict[str, list[str]],
    participants_and_sessions_downloaded: Optional[dict[str, list[str]]] = None,
    participants_and_sessions_organized: Optional[dict[str, list[str]]] = None,
    participants_and_sessions_converted: Optional[dict[str, list[str]]] = None,
    dpath_downloaded: Optional[str | Path] = None,
    dpath_organized: Optional[str | Path] = None,
    dpath_converted: Optional[str | Path] = None,
):
    # create the manifest
    data_manifest = []
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
    manifest = Manifest(data_manifest)

    # create fake downloaded DICOMs
    if (
        participants_and_sessions_downloaded is not None
        and dpath_downloaded is not None
    ):
        fake_dicoms_downloaded(
            dpath_downloaded,
            participants_and_sessions_downloaded,
        )

    # create fake organized DICOMs
    if participants_and_sessions_organized is not None and dpath_organized is not None:
        fake_dicoms_organized(
            dpath_organized,
            participants_and_sessions_organized,
        )

    # create fake BIDS dataset
    if participants_and_sessions_converted is not None and dpath_converted is not None:
        for participant, sessions in participants_and_sessions_converted.items():
            create_fake_bids_dataset(
                Path(dpath_converted),
                subjects=participant,
                sessions=[strip_session(session) for session in sessions],
                datatypes=["anat"],
            )

    return manifest


def _check_doughnut(
    doughnut: Doughnut,
    participants_and_sessions_manifest,
    participants_and_sessions_downloaded,
    participants_and_sessions_organized,
    participants_and_sessions_converted,
    empty,
):
    if empty:
        for col in [
            doughnut.col_downloaded,
            doughnut.col_organized,
            doughnut.col_converted,
        ]:
            assert (~doughnut[col]).all()
    else:
        for participant in participants_and_sessions_manifest:
            for session in participants_and_sessions_manifest[participant]:
                for col, participants_and_sessions_true in {
                    doughnut.col_downloaded: participants_and_sessions_downloaded,
                    doughnut.col_organized: participants_and_sessions_organized,
                    doughnut.col_converted: participants_and_sessions_converted,
                }.items():
                    status: pd.Series = doughnut.loc[
                        (doughnut[doughnut.col_participant_id] == participant)
                        & (doughnut[doughnut.col_session] == session),
                        col,
                    ]

                    assert len(status) == 1
                    status = status.iloc[0]

                    assert status == (
                        participant in participants_and_sessions_true
                        and session in participants_and_sessions_true[participant]
                    )


@pytest.mark.parametrize(
    (
        "participants_and_sessions_manifest1"
        ",participants_and_sessions_manifest2"
        ",participants_and_sessions_downloaded"
        ",participants_and_sessions_organized"
        ",participants_and_sessions_converted"
        ",dpath_downloaded_relative"
        ",dpath_organized_relative"
        ",dpath_converted_relative"
    ),
    [
        (
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL", "ses-M12"]},
            {
                "01": ["ses-BL", "ses-M12"],
                "02": ["ses-BL", "ses-M12"],
                "03": ["ses-BL", "ses-M12"],
            },
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL"]},
            {"01": ["ses-BL"], "02": ["ses-BL"], "03": ["ses-BL"]},
            {"01": ["ses-BL", "ses-M12"], "03": ["ses-M12"]},
            "downloaded",
            "organized",
            "converted",
        ),
        (
            {"PD01": ["ses-BL"], "PD02": ["ses-BL"]},
            {"PD01": ["ses-BL", "ses-M12"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL", "ses-M12"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL"], "PD02": ["ses-BL"]},
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
    participants_and_sessions_converted: dict[str, list[str]],
    dpath_downloaded_relative: str | Path,
    dpath_organized_relative: str | Path,
    dpath_converted_relative: str | Path,
    empty: bool,
    str_paths: bool,
    tmp_path: Path,
):
    dpath_root = tmp_path / "my_dataset"
    dpath_downloaded = dpath_root / dpath_downloaded_relative
    dpath_organized = dpath_root / dpath_organized_relative
    dpath_converted = dpath_root / dpath_converted_relative

    if str_paths:
        dpath_downloaded = str(dpath_downloaded)
        dpath_organized = str(dpath_organized)
        dpath_converted = str(dpath_converted)

    # create the manifest
    manifest1 = _prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_converted=dpath_converted,
    )

    # generate the doughnut
    doughnut1 = generate_doughnut(
        manifest=manifest1,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_converted=dpath_converted,
        empty=empty,
    )
    # the doughnut should have the same number of records as the manifest
    assert len(doughnut1) == len(manifest1)

    _check_doughnut(
        doughnut=doughnut1,
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        empty=empty,
    )

    # create a new manifest
    manifest2 = _prepare_dataset(participants_and_sessions_manifest2)
    doughnut2 = update_doughnut(
        doughnut=doughnut1,
        manifest=manifest2,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_converted=dpath_converted,
        empty=empty,
    )
    assert len(doughnut2) == len(manifest2)

    _check_doughnut(
        doughnut=doughnut2,
        participants_and_sessions_manifest=participants_and_sessions_manifest2,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        empty=empty,
    )


def test_generate_missing_paths(tmp_path: Path):
    participants_and_sessions = {
        "01": ["ses-BL", "ses-M12"],
        "02": ["ses-BL", "ses-M12"],
    }

    dpath_root = tmp_path / "my_dataset"
    dpath_downloaded = dpath_root / "downloaded"
    dpath_organized = None
    dpath_converted = dpath_root / "bids"

    manifest = _prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_downloaded=participants_and_sessions,
        participants_and_sessions_organized=participants_and_sessions,
        participants_and_sessions_converted=participants_and_sessions,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_converted=dpath_converted,
    )

    doughnut = generate_doughnut(
        manifest=manifest,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_converted=dpath_converted,
        empty=False,
    )

    assert doughnut[Doughnut.col_downloaded].all()
    assert (~doughnut[Doughnut.col_organized]).all()
    assert doughnut[Doughnut.col_converted].all()


@pytest.mark.parametrize(
    (
        "participants_and_sessions_manifest1"
        ",participants_and_sessions_manifest2"
        ",participants_and_sessions_downloaded"
        ",participants_and_sessions_organized"
        ",participants_and_sessions_converted"
    ),
    [
        (
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL", "ses-M12"]},
            {
                "01": ["ses-BL", "ses-M12"],
                "02": ["ses-BL", "ses-M12"],
                "03": ["ses-BL", "ses-M12"],
            },
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL"]},
            {"01": ["ses-BL"], "02": ["ses-BL"], "03": ["ses-BL"]},
            {"01": ["ses-BL", "ses-M12"], "03": ["ses-M12"]},
        ),
        (
            {"PD01": ["ses-BL"], "PD02": ["ses-BL"]},
            {"PD01": ["ses-BL", "ses-M12"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL", "ses-M12"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL"], "PD02": ["ses-BL"]},
        ),
    ],
)
@pytest.mark.parametrize("empty", [True, False])
def test_doughnut_workflow(
    participants_and_sessions_manifest1: dict[str, list[str]],
    participants_and_sessions_manifest2: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_converted: dict[str, list[str]],
    empty: bool,
    tmp_path: Path,
):
    dpath_root = tmp_path / "my_dataset"

    dpath_downloaded = dpath_root / ATTR_TO_DPATH_MAP["dpath_raw_dicom"]
    dpath_organized = dpath_root / ATTR_TO_DPATH_MAP["dpath_dicom"]
    dpath_converted = dpath_root / ATTR_TO_DPATH_MAP["dpath_bids"]
    fpath_manifest = dpath_root / ATTR_TO_FPATH_MAP["fpath_manifest"]
    fpath_config = dpath_root / ATTR_TO_FPATH_MAP["fpath_config"]
    fpath_doughnut = dpath_root / ATTR_TO_FPATH_MAP["fpath_doughnut"]

    manifest1 = _prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_converted=dpath_converted,
    )
    manifest1.save_with_backup(fpath_manifest)

    # prepare config file
    config = Config(
        DATASET_NAME="my_dataset",
        DATASET_ROOT=dpath_root,
        CONTAINER_STORE="fake_path",
        SESSIONS=list(manifest1[Manifest.col_session].unique()),
        BIDS={},
        PROC_PIPELINES={},
    )
    save_json(config.model_dump(mode="json"), fpath_config)

    # generate the doughnut
    DoughnutWorkflow(dpath_root=dpath_root, empty=empty).run()
    doughnut1 = Doughnut.load(fpath_doughnut)

    assert len(doughnut1) == len(manifest1)
    _check_doughnut(
        doughnut=doughnut1,
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        empty=empty,
    )

    # update the manifest
    manifest2 = _prepare_dataset(participants_and_sessions_manifest2)
    manifest2.save_with_backup(fpath_manifest)

    # update the doughnut
    DoughnutWorkflow(dpath_root=dpath_root, empty=empty).run()
    doughnut2 = Doughnut.load(fpath_doughnut)

    assert len(doughnut2) == len(manifest2)
    _check_doughnut(
        doughnut=doughnut2,
        participants_and_sessions_manifest=participants_and_sessions_manifest2,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        empty=empty,
    )


@pytest.mark.parametrize(
    (
        "participants_and_sessions_manifest"
        ",participants_and_sessions_downloaded"
        ",participants_and_sessions_organized"
        ",participants_and_sessions_converted"
    ),
    [
        (
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL", "ses-M12"]},
            {"01": ["ses-BL", "ses-M12"], "02": ["ses-BL"]},
            {"01": ["ses-BL"], "02": ["ses-BL"], "03": ["ses-BL"]},
            {"01": ["ses-BL", "ses-M12"], "03": ["ses-M12"]},
        ),
        (
            {"PD01": ["ses-BL", "ses-M12"], "PD02": ["ses-BL"]},
            {"PD01": ["ses-BL", "ses-M12"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL"], "PD02": ["ses-BL", "ses-M12"]},
            {"PD01": ["ses-BL"], "PD02": ["ses-BL"]},
        ),
    ],
)
@pytest.mark.parametrize("empty", [True, False])
def test_doughnut_workflow_regenerate(
    participants_and_sessions_manifest: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_converted: dict[str, list[str]],
    empty: bool,
    tmp_path: Path,
):
    dpath_root = tmp_path / "my_dataset"

    dpath_downloaded = dpath_root / ATTR_TO_DPATH_MAP["dpath_raw_dicom"]
    dpath_organized = dpath_root / ATTR_TO_DPATH_MAP["dpath_dicom"]
    dpath_converted = dpath_root / ATTR_TO_DPATH_MAP["dpath_bids"]
    fpath_manifest = dpath_root / ATTR_TO_FPATH_MAP["fpath_manifest"]
    fpath_config = dpath_root / ATTR_TO_FPATH_MAP["fpath_config"]
    fpath_doughnut = dpath_root / ATTR_TO_FPATH_MAP["fpath_doughnut"]

    manifest = _prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        dpath_downloaded=dpath_downloaded,
        dpath_organized=dpath_organized,
        dpath_converted=dpath_converted,
    )
    manifest.save_with_backup(fpath_manifest)

    # prepare config file
    config = Config(
        DATASET_NAME="my_dataset",
        DATASET_ROOT=dpath_root,
        CONTAINER_STORE="fake_path",
        SESSIONS=list(manifest[Manifest.col_session].unique()),
        BIDS={},
        PROC_PIPELINES={},
    )
    save_json(config.model_dump(mode="json"), fpath_config)

    # to be overwritten
    doughnut_records = []
    for _, manifest_record in manifest.iterrows():
        participant = manifest_record[Manifest.col_participant_id]
        doughnut_records.append(
            {
                Doughnut.col_participant_id: participant,
                Doughnut.col_visit: manifest_record[Manifest.col_visit],
                Doughnut.col_session: manifest_record[Manifest.col_session],
                Doughnut.col_datatype: manifest_record[Manifest.col_datatype],
                Doughnut.col_participant_dicom_dir: participant,
                Doughnut.col_dicom_id: participant,
                Doughnut.col_bids_id: f"sub-{participant}",
                Doughnut.col_downloaded: True,
                Doughnut.col_organized: True,
                Doughnut.col_converted: True,
            }
        )
    doughnut_old = Doughnut(doughnut_records)
    assert doughnut_old.save_with_backup(fpath_doughnut) is not None

    # regenerate the doughnut
    DoughnutWorkflow(dpath_root=dpath_root, empty=empty, regenerate=True).run()
    doughnut = Doughnut.load(fpath_doughnut)

    assert len(doughnut) == len(manifest)
    _check_doughnut(
        doughnut=doughnut,
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_converted=participants_and_sessions_converted,
        empty=empty,
    )
