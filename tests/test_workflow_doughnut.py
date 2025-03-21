"""Tests for the DoughnutWorkflow."""

from pathlib import Path

import pytest

from nipoppy.tabular.doughnut import Doughnut
from nipoppy.tabular.manifest import Manifest
from nipoppy.workflows.doughnut import DoughnutWorkflow

from .conftest import check_doughnut, create_empty_dataset, get_config, prepare_dataset


@pytest.fixture(scope="function")
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)
    workflow = DoughnutWorkflow(dpath_root=dpath_root)
    workflow.config = get_config()
    workflow.config.save(workflow.layout.fpath_config)
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
    workflow: DoughnutWorkflow,
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
        dpath_downloaded=workflow.layout.dpath_pre_reorg,
        dpath_organized=workflow.layout.dpath_post_reorg,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    workflow.manifest = manifest1

    # generate the doughnut
    workflow.run_main()
    doughnut1 = Doughnut.load(workflow.layout.fpath_doughnut)

    assert len(doughnut1) == len(manifest1)
    check_doughnut(
        doughnut=doughnut1,
        participants_and_sessions_manifest=participants_and_sessions_manifest1,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )

    # update the manifest (add rows)
    manifest2 = prepare_dataset(participants_and_sessions_manifest2)
    manifest2.save_with_backup(workflow.layout.fpath_manifest)

    # update the doughnut
    DoughnutWorkflow(dpath_root=workflow.dpath_root, empty=empty).run_main()
    doughnut2 = Doughnut.load(workflow.layout.fpath_doughnut)

    assert len(doughnut2) == len(manifest2)
    check_doughnut(
        doughnut=doughnut2,
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
    workflow: DoughnutWorkflow,
    participants_and_sessions_manifest: dict[str, list[str]],
    participants_and_sessions_downloaded: dict[str, list[str]],
    participants_and_sessions_organized: dict[str, list[str]],
    participants_and_sessions_bidsified: dict[str, list[str]],
    empty: bool,
):
    workflow.empty = empty
    workflow.regenerate = True

    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_downloaded=workflow.layout.dpath_pre_reorg,
        dpath_organized=workflow.layout.dpath_post_reorg,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    workflow.manifest = manifest

    # to be overwritten
    doughnut_records = []
    for _, manifest_record in manifest.iterrows():
        participant_id = manifest_record[Manifest.col_participant_id]
        doughnut_records.append(
            {
                Doughnut.col_participant_id: participant_id,
                Doughnut.col_visit_id: manifest_record[Manifest.col_visit_id],
                Doughnut.col_session_id: manifest_record[Manifest.col_session_id],
                Doughnut.col_datatype: manifest_record[Manifest.col_datatype],
                Doughnut.col_participant_dicom_dir: participant_id,
                Doughnut.col_in_pre_reorg: True,
                Doughnut.col_in_post_reorg: True,
                Doughnut.col_in_bids: True,
            }
        )
    doughnut_old = Doughnut(doughnut_records)
    assert doughnut_old.save_with_backup(workflow.layout.fpath_doughnut) is not None

    # regenerate the doughnut
    workflow.run_main()
    doughnut = Doughnut.load(workflow.layout.fpath_doughnut)

    assert len(doughnut) == len(manifest)
    check_doughnut(
        doughnut=doughnut,
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        empty=empty,
    )


def test_run_cleanup(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    DoughnutWorkflow(dpath_root=tmp_path).run_cleanup()
    assert "Successfully generated/updated the dataset's doughnut file!" in caplog.text
