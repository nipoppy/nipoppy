"""Tests for the DoughnutWorkflow."""

from pathlib import Path

import pytest
from conftest import (
    ATTR_TO_DPATH_MAP,
    ATTR_TO_FPATH_MAP,
    _check_doughnut,
    _prepare_dataset,
)

from nipoppy.config.base import Config
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import save_json
from nipoppy.workflows.doughnut import DoughnutWorkflow


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
