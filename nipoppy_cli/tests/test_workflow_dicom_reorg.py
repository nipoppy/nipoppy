"""Tests for DicomReorgWorkflow."""

from pathlib import Path

import pytest

from nipoppy.tabular.manifest import Manifest
from nipoppy.workflows.dicom_reorg import DicomReorgWorkflow

from .conftest import create_empty_dataset, get_config, prepare_dataset


@pytest.mark.parametrize(
    "participant,session,fpaths,participant_first",
    [
        ("01", "ses-1", ["01/ses-1/file1.dcm", "01/ses-1/file2.dcm"], True),
        (
            "02",
            "ses-2",
            ["ses-2/02/001.dcm", "ses-2/02/002.dcm", "ses-2/02/003.dcm"],
            False,
        ),
    ],
)
def test_get_fpaths_to_reorg(
    participant, session, fpaths, participant_first, tmp_path: Path
):
    dpath_root = tmp_path / "my_dataset"

    workflow = DicomReorgWorkflow(dpath_root=dpath_root)
    for fpath in fpaths:
        fpath_full = workflow.layout.dpath_raw_dicom / fpath
        fpath_full.parent.mkdir(parents=True, exist_ok=True)
        fpath_full.touch()

    assert len(
        workflow.get_fpaths_to_reorg(
            participant=participant,
            session=session,
            participant_first=participant_first,
        )
    ) == len(fpaths)


def test_get_fpaths_to_reorg_error_not_found(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=dpath_root)

    with pytest.raises(FileNotFoundError, match="Raw DICOM directory not found"):
        workflow.get_fpaths_to_reorg("XXX", "ses-X")


@pytest.mark.parametrize(
    "mapping_func,expected",
    [
        (lambda fname, participant, session: fname, "123456.dcm"),
        (lambda fname, participant, session: "dicoms.tar.gz", "dicoms.tar.gz"),
        (
            lambda fname, participant, session: f"{participant}-{session}.tar.gz",
            "01-ses-1.tar.gz",
        ),
    ],
)
def test_apply_fname_mapping(mapping_func, expected, tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=dpath_root)
    workflow.apply_fname_mapping = mapping_func

    fname = "123456.dcm"
    participant = "01"
    session = "ses-1"
    assert workflow.apply_fname_mapping(fname, participant, session) == expected


@pytest.mark.parametrize(
    "fname_source,expected",
    [
        ("123456.dcm", "123456.dcm"),
        (Path("123456.dcm"), Path("123456.dcm")),
        ("dicoms.tar.gz", "dicoms.tar.gz"),
    ],
)
def test_apply_fname_mapping_default(fname_source, expected, tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=dpath_root)

    assert (
        workflow.apply_fname_mapping(
            fname_source=fname_source, participant="", session=""
        )
        == expected
    )


def test_run_single_error_file_exists(tmp_path: Path):
    participant = "01"
    session = "ses-1"
    dataset_name = "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=tmp_path / dataset_name)

    # create the same file in both the downloaded and organized directories
    fname = "test.dcm"
    for fpath in [
        workflow.layout.dpath_raw_dicom / session / participant / fname,
        workflow.layout.dpath_sourcedata / participant / session / fname,
    ]:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    with pytest.raises(FileExistsError, match="Cannot move file"):
        workflow.run_single(participant, session)


def test_copy_files_default(tmp_path: Path):
    dataset_name = "my_dataset"
    workflow = DicomReorgWorkflow(dpath_root=tmp_path / dataset_name)
    assert workflow.copy_files is False


@pytest.mark.parametrize(
    "participants_and_sessions_manifest,participants_and_sessions_downloaded",
    [
        (
            {
                "S01": ["ses-1", "ses-2", "ses-3"],
                "S02": ["ses-1", "ses-2", "ses-3"],
                "S03": ["ses-1", "ses-2", "ses-3"],
            },
            {
                "S01": ["ses-1", "ses-2", "ses-3"],
                "S02": ["ses-1", "ses-2"],
                "S03": ["ses-3"],
            },
        ),
        (
            {
                "P01": ["ses-BL"],
                "P02": ["ses-V01"],
                "P03": ["ses-V03"],
            },
            {
                "P01": ["ses-BL"],
                "P02": ["ses-BL", "ses-V01"],
                "P03": ["ses-BL", "ses-V03"],
            },
        ),
    ],
)
@pytest.mark.parametrize("copy_files", [True, False])
def test_run(
    participants_and_sessions_manifest: dict,
    participants_and_sessions_downloaded: dict,
    copy_files: bool,
    tmp_path: Path,
):
    dataset_name = "my_dataset"
    workflow = DicomReorgWorkflow(
        dpath_root=tmp_path / dataset_name, copy_files=copy_files
    )
    create_empty_dataset(workflow.layout.dpath_root)

    manifest: Manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_downloaded=participants_and_sessions_downloaded,
        dpath_downloaded=workflow.layout.dpath_raw_dicom,
    )

    config = get_config(
        dataset_name=dataset_name,
        visits=list(manifest[Manifest.col_visit].unique()),
    )

    manifest.save_with_backup(workflow.layout.fpath_manifest)
    config.save(workflow.layout.fpath_config)

    workflow.run()

    for participant, sessions in participants_and_sessions_manifest.items():
        for session in sessions:
            dpath_to_check: Path = (
                workflow.layout.dpath_sourcedata / participant / session
            )

            if (
                participant in participants_and_sessions_downloaded
                and session in participants_and_sessions_downloaded[participant]
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

                # check that the doughnut has been updated
                assert workflow.doughnut.get_status(
                    participant, session, workflow.doughnut.col_organized
                )

            else:
                assert not dpath_to_check.exists()
