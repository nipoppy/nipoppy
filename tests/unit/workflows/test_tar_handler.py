"""Tests for TAR workflow helper."""

import tarfile
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.exceptions import ConfigError, FileOperationError
from nipoppy.workflows.tar_handler import TarHandler


@pytest.fixture
def tar_handler() -> TarHandler:
    return TarHandler()


def test_validate_preconditions_no_tracker_config(tar_handler: TarHandler):
    with pytest.raises(
        ConfigError,
        match="Tarring requested but there is no tracker config file",
    ):
        tar_handler.validate_preconditions(
            tar_requested=True,
            tracker_config_file=None,
            participant_session_dir="sub-01/ses-1",
        )


def test_validate_preconditions_no_participant_session_dir(
    tar_handler: TarHandler, tmp_path: Path
):
    with pytest.raises(
        ConfigError,
        match="Tarring requested but no participant-session directory specified",
    ):
        tar_handler.validate_preconditions(
            tar_requested=True,
            tracker_config_file=tmp_path / "tracker_config.json",
            participant_session_dir=None,
        )


def test_validate_preconditions_no_tar_requested(tar_handler: TarHandler):
    tar_handler.validate_preconditions(
        tar_requested=False,
        tracker_config_file=None,
        participant_session_dir=None,
    )


@pytest.mark.parametrize("dpath_type", [Path, str])
def test_tar_directory(tmp_path: Path, dpath_type):
    dpath_to_tar = tmp_path / "my_data"
    fpaths_to_tar = [
        dpath_to_tar / "dir1" / "file1.txt",
        dpath_to_tar / "file2.txt",
    ]
    for fpath in fpaths_to_tar:
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    fpath_tarred = TarHandler().tar_directory(dpath_type(dpath_to_tar))

    assert fpath_tarred == dpath_to_tar.with_suffix(".tar")
    assert fpath_tarred.exists()
    assert fpath_tarred.is_file()

    with tarfile.open(fpath_tarred, "r") as tar:
        tarred_files = {
            tmp_path / tarred.name for tarred in tar.getmembers() if tarred.isfile()
        }
    assert tarred_files == set(fpaths_to_tar)
    assert not dpath_to_tar.exists()


@pytest.mark.no_xdist
def test_tar_directory_failure(
    tar_handler: TarHandler,
    tmp_path: Path,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    dpath_to_tar = tmp_path / "my_data"
    fpath_to_tar = dpath_to_tar / "file.txt"
    fpath_to_tar.parent.mkdir(parents=True)
    fpath_to_tar.touch()

    mocked_is_tarfile = mocker.patch(
        "nipoppy.workflows.tar_handler.is_tarfile", return_value=False
    )

    fpath_tarred = tar_handler.tar_directory(dpath_to_tar)

    assert fpath_tarred.exists()
    mocked_is_tarfile.assert_called_once()
    assert f"Failed to tar {dpath_to_tar}" in caplog.text


def test_tar_directory_warning_not_found(tar_handler: TarHandler):
    with pytest.raises(
        FileOperationError, match="Not tarring .* since it does not exist"
    ):
        tar_handler.tar_directory("invalid_path")


def test_tar_directory_warning_not_dir(tar_handler: TarHandler, tmp_path: Path):
    fpath_to_tar = tmp_path / "file.txt"
    fpath_to_tar.touch()

    with pytest.raises(
        FileOperationError, match="Not tarring .* since it is not a directory"
    ):
        tar_handler.tar_directory(fpath_to_tar)
