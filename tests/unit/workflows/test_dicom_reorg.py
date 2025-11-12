"""Tests for DicomReorgWorkflow."""

import logging
import shutil
from pathlib import Path

import pytest

from nipoppy.env import ReturnCode
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils.bids import (
    participant_id_to_bids_participant_id,
    session_id_to_bids_session_id,
)
from nipoppy.workflows.dicom_reorg import DicomReorgWorkflow, is_derived_dicom
from tests.conftest import (
    DPATH_TEST_DATA,
    create_empty_dataset,
    get_config,
    prepare_dataset,
)


@pytest.fixture()
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=dpath_root)
    workflow.study.config = get_config()
    workflow.study.config.save(workflow.study.layout.fpath_config)
    return workflow


def test_init_attributes(workflow: DicomReorgWorkflow):
    assert workflow.copy_files is False
    assert workflow.check_dicoms is False
    assert workflow.n_success == 0
    assert workflow.n_total == 0


@pytest.mark.parametrize(
    "fpath,expected_result",
    [
        (DPATH_TEST_DATA / "dicom-not_derived.dcm", False),
        (DPATH_TEST_DATA / "dicom-derived.dcm", True),
    ],
)
def test_is_derived_dicom(fpath, expected_result):
    assert is_derived_dicom(fpath) == expected_result


@pytest.mark.parametrize(
    "participant_id,session_id,fpaths,participant_first",
    [
        ("01", "1", ["01/1/file1.dcm", "01/1/file2.dcm"], True),
        (
            "02",
            "2",
            ["2/02/001.dcm", "2/02/002.dcm", "2/02/003.dcm"],
            False,
        ),
    ],
)
def test_get_fpaths_to_reorg(
    workflow: DicomReorgWorkflow, participant_id, session_id, fpaths, participant_first
):
    manifest = prepare_dataset(
        participants_and_sessions_manifest={participant_id: [session_id]}
    )

    workflow.dicom_dir_map = DicomDirMap.load_or_generate(
        manifest=manifest, fpath_dicom_dir_map=None, participant_first=participant_first
    )
    for fpath in fpaths:
        fpath_full: Path = workflow.study.layout.dpath_pre_reorg / fpath
        fpath_full.parent.mkdir(parents=True, exist_ok=True)
        fpath_full.touch()

    assert len(
        workflow.get_fpaths_to_reorg(
            participant_id=participant_id,
            session_id=session_id,
        )
    ) == len(fpaths)


def test_get_fpaths_to_reorg_error_not_found(workflow: DicomReorgWorkflow):
    participant_id = "XXX"
    session_id = "X"
    manifest = prepare_dataset(
        participants_and_sessions_manifest={participant_id: [session_id]}
    )
    workflow.dicom_dir_map = DicomDirMap.load_or_generate(
        manifest=manifest, fpath_dicom_dir_map=None, participant_first=True
    )

    with pytest.raises(FileNotFoundError, match="Raw DICOM directory not found"):
        workflow.get_fpaths_to_reorg("XXX", "X")


@pytest.mark.parametrize(
    "mapping_func,expected",
    [
        (lambda fname, participant_id, session_id: fname, "123456.dcm"),
        (lambda fname, participant_id, session_id: "dicoms.tar.gz", "dicoms.tar.gz"),
        (
            lambda fname, participant_id, session_id: (
                f"{participant_id}-{session_id}.tar.gz"
            ),
            "01-1.tar.gz",
        ),
    ],
)
def test_apply_fname_mapping(workflow: DicomReorgWorkflow, mapping_func, expected):
    workflow.apply_fname_mapping = mapping_func
    fname = "123456.dcm"
    participant_id = "01"
    session_id = "1"
    assert workflow.apply_fname_mapping(fname, participant_id, session_id) == expected


@pytest.mark.parametrize(
    "fpath_source,expected",
    [
        ("123456.dcm", "123456.dcm"),
        (Path("dirA", "123456.dcm"), "123456.dcm"),
        ("123/dicoms.tar.gz", "dicoms.tar.gz"),
    ],
)
def test_apply_fname_mapping_default(
    workflow: DicomReorgWorkflow, fpath_source, expected
):
    assert (
        workflow.apply_fname_mapping(
            fpath_source=fpath_source, participant_id="", session_id=""
        )
        == expected
    )


def test_run_single_error_file_exists(workflow: DicomReorgWorkflow):
    participant_id = "01"
    session_id = "1"
    manifest = prepare_dataset(
        participants_and_sessions_manifest={participant_id: [session_id]}
    )
    workflow.dicom_dir_map = DicomDirMap.load_or_generate(
        manifest=manifest, fpath_dicom_dir_map=None, participant_first=True
    )

    # create the same file in both the downloaded and organized directories
    fname = "test.dcm"
    for fpath in [
        workflow.study.layout.dpath_pre_reorg / participant_id / session_id / fname,
        workflow.study.layout.dpath_post_reorg
        / participant_id_to_bids_participant_id(participant_id)
        / session_id_to_bids_session_id(session_id)
        / fname,
    ]:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    with pytest.raises(FileExistsError, match="Cannot move file"):
        workflow.run_single(participant_id, session_id)


def test_run_single_invalid_dicom(
    workflow: DicomReorgWorkflow, caplog: pytest.LogCaptureFixture
):
    participant_id = "01"
    session_id = "1"
    workflow.check_dicoms = True

    manifest = prepare_dataset(
        participants_and_sessions_manifest={participant_id: [session_id]}
    )
    workflow.dicom_dir_map = DicomDirMap.load_or_generate(
        manifest=manifest, fpath_dicom_dir_map=None, participant_first=True
    )

    # use derived DICOM file
    fpath_dicom = (
        workflow.study.layout.dpath_pre_reorg / participant_id / session_id / "test.dcm"
    )
    fpath_dicom.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DPATH_TEST_DATA / "dicom-derived.dcm", fpath_dicom)

    try:
        workflow.run_single(participant_id, session_id)
    except Exception:
        pass

    assert any(
        [
            "Derived DICOM file detected" in record.message
            and record.levelno == logging.WARNING
            for record in caplog.records
        ]
    )


def test_run_single_error_dicom_read(workflow: DicomReorgWorkflow):
    participant_id = "01"
    session_id = "1"
    workflow.check_dicoms = True

    manifest = prepare_dataset(
        participants_and_sessions_manifest={participant_id: [session_id]}
    )
    workflow.dicom_dir_map = DicomDirMap.load_or_generate(
        manifest=manifest, fpath_dicom_dir_map=None, participant_first=True
    )

    # create an invalid DICOM file
    fname = "test.dcm"
    fpath = workflow.study.layout.dpath_pre_reorg / participant_id / session_id / fname
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.touch()

    with pytest.raises(RuntimeError, match="Error checking DICOM file"):
        workflow.run_single(participant_id, session_id)


@pytest.mark.parametrize(
    (
        "participants_and_sessions_downloaded"
        ",participants_and_sessions_organized"
        ",expected"
    ),
    [
        (
            {
                "S01": ["1", "2", "3"],
                "S02": ["1", "2"],
                "S03": ["3"],
            },
            {
                "S03": ["3"],
            },
            [
                ("S01", "1"),
                ("S01", "2"),
                ("S01", "3"),
                ("S02", "1"),
                ("S02", "2"),
            ],
        ),
        (
            {
                "S01": ["1", "2", "3"],
                "S02": ["1", "2", "3"],
                "S03": ["1", "2", "3"],
            },
            {
                "S01": ["1", "3"],
            },
            [
                ("S01", "2"),
                ("S02", "1"),
                ("S02", "2"),
                ("S02", "3"),
                ("S03", "1"),
                ("S03", "2"),
                ("S03", "3"),
            ],
        ),
    ],
)
def test_get_participants_sessions_to_run(
    workflow: DicomReorgWorkflow,
    participants_and_sessions_downloaded,
    participants_and_sessions_organized,
    expected,
):
    participants_and_sessions_manifest = {
        "S01": ["1", "2", "3"],
        "S02": ["1", "2", "3"],
        "S03": ["1", "2", "3"],
    }
    create_empty_dataset(workflow.study.layout.dpath_root)

    manifest: Manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        participants_and_sessions_organized=participants_and_sessions_organized,
        dpath_downloaded=workflow.study.layout.dpath_pre_reorg,
        dpath_organized=workflow.study.layout.dpath_post_reorg,
    )
    manifest.save_with_backup(workflow.study.layout.fpath_manifest)

    assert [tuple(x) for x in workflow.get_participants_sessions_to_run()] == expected


def test_run_setup(workflow: DicomReorgWorkflow):
    participants_and_sessions1 = {"01": ["1"]}
    participants_and_sessions2 = {"01": ["1", "2"], "02": ["1"]}

    create_empty_dataset(workflow.study.layout.dpath_root)

    manifest1 = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions1,
    )
    manifest1.save_with_backup(workflow.study.layout.fpath_manifest)

    # generate first curation status table with the smaller manifest
    curation_status_table1 = DicomReorgWorkflow(
        dpath_root=workflow.dpath_root
    ).curation_status_table

    # update manifest
    manifest2 = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions2,
    )
    manifest2.save_with_backup(workflow.study.layout.fpath_manifest)
    workflow.manifest = manifest2

    # check that curation status table was regenerated
    workflow.run_setup()

    assert not workflow.curation_status_table.equals(curation_status_table1)
    assert len(workflow.curation_status_table) == len(manifest2)


@pytest.mark.parametrize(
    "participants_and_sessions_manifest,participants_and_sessions_downloaded",
    [
        (
            {
                "S01": ["1", "2", "3"],
                "S02": ["1", "2", "3"],
                "S03": ["1", "2", "3"],
            },
            {
                "S01": ["1", "2", "3"],
                "S02": ["1", "2"],
                "S03": ["3"],
            },
        ),
        (
            {
                "P01": ["BL"],
                "P02": ["V01"],
                "P03": ["V03"],
            },
            {
                "P01": ["BL"],
                "P02": ["BL", "V01"],
                "P03": ["BL", "V03"],
            },
        ),
    ],
)
@pytest.mark.parametrize("copy_files", [True, False])
def test_run_main(
    workflow: DicomReorgWorkflow,
    participants_and_sessions_manifest: dict,
    participants_and_sessions_downloaded: dict,
    copy_files: bool,
):
    workflow.copy_files = copy_files

    manifest: Manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        dpath_downloaded=workflow.study.layout.dpath_pre_reorg,
    )
    manifest.save_with_backup(workflow.study.layout.fpath_manifest)

    workflow.run_main()

    for participant_id, session_ids in participants_and_sessions_manifest.items():
        for session_id in session_ids:
            dpath_to_check: Path = (
                workflow.study.layout.dpath_post_reorg
                / participant_id_to_bids_participant_id(participant_id)
                / session_id_to_bids_session_id(session_id)
            )

            if (
                participant_id in participants_and_sessions_downloaded
                and session_id in participants_and_sessions_downloaded[participant_id]
            ):
                # check that directory exists
                assert dpath_to_check.exists()

                # make sure it is not empty
                # and that symlinks are created if requested
                count = 0
                for fpath in dpath_to_check.iterdir():
                    if copy_files:
                        assert not fpath.is_symlink()
                    else:
                        assert fpath.is_symlink()
                    count += 1
                assert count > 0

                # check that the curation status table has been updated
                assert workflow.curation_status_table.get_status(
                    participant_id=participant_id,
                    session_id=session_id,
                    col=workflow.curation_status_table.col_in_post_reorg,
                )

            else:
                assert not dpath_to_check.exists()

    assert workflow.n_total != 0
    assert workflow.n_success == workflow.n_total


def test_run_main_error(workflow: DicomReorgWorkflow):
    create_empty_dataset(workflow.study.layout.dpath_root)

    manifest: Manifest = prepare_dataset(
        participants_and_sessions_manifest={
            "S01": ["1", "2", "3"],
            "S02": ["1", "2", "3"],
            "S03": ["1", "2", "3"],
        },
    )
    manifest.save_with_backup(workflow.study.layout.fpath_manifest)

    # will cause the workflow to fail because the directories cannot be found
    workflow.curation_status_table[workflow.curation_status_table.col_in_pre_reorg] = (
        True
    )

    try:
        workflow.run_main()
    except Exception:
        pass

    assert workflow.return_code == ReturnCode.PARTIAL_SUCCESS


@pytest.mark.parametrize(
    "curation_status_table",
    [
        CurationStatusTable(),
        CurationStatusTable(
            data={
                CurationStatusTable.col_participant_id: ["01"],
                CurationStatusTable.col_visit_id: ["1"],
                CurationStatusTable.col_session_id: ["1"],
                CurationStatusTable.col_datatype: "['anat']",
                CurationStatusTable.col_participant_dicom_dir: ["01"],
                CurationStatusTable.col_in_pre_reorg: [True],
                CurationStatusTable.col_in_post_reorg: [True],
                CurationStatusTable.col_in_bids: [True],
            }
        ).validate(),
    ],
)
def test_cleanup_curation_status(
    workflow: DicomReorgWorkflow, curation_status_table: CurationStatusTable
):
    workflow.curation_status_table = curation_status_table
    workflow.run_cleanup()

    assert workflow.study.layout.fpath_curation_status.exists()
    assert CurationStatusTable.load(workflow.study.layout.fpath_curation_status).equals(
        curation_status_table
    )


@pytest.mark.parametrize(
    "n_success,n_total,expected_message",
    [
        (0, 0, "No participant-session pairs to reorganize"),
        (
            0,
            1,
            "Reorganized files for {0} out of {1} participant-session pairs",
        ),
        (
            1,
            2,
            "Reorganized files for {0} out of {1} participant-session pairs",
        ),
        (
            2,
            2,
            "Reorganized files for {0} out of {1} participant-session pairs",
        ),
    ],
)
def test_run_cleanup_message(
    workflow: DicomReorgWorkflow,
    n_success,
    n_total,
    expected_message: str,
    caplog: pytest.LogCaptureFixture,
):
    workflow.curation_status_table = CurationStatusTable()  # empty table to avoid error
    workflow.n_success = n_success
    workflow.n_total = n_total
    workflow.run_cleanup()

    assert expected_message.format(n_success, n_total) in caplog.text
