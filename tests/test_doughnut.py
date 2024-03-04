"""Tests for the manifest."""

from contextlib import nullcontext
from pathlib import Path

import pytest
from conftest import DPATH_TEST_DATA, _check_doughnut, _prepare_dataset

from nipoppy.tabular.doughnut import Doughnut, generate_doughnut, update_doughnut


@pytest.mark.parametrize(
    "fpath",
    [
        DPATH_TEST_DATA / "doughnut1.csv",
        DPATH_TEST_DATA / "doughnut2.csv",
    ],
)
@pytest.mark.parametrize("validate", [True, False])
def test_load(fpath, validate):
    assert isinstance(Doughnut.load(fpath, validate=validate), Doughnut)


@pytest.mark.parametrize(
    "fpath,is_valid",
    [
        (DPATH_TEST_DATA / "doughnut1.csv", True),
        (DPATH_TEST_DATA / "doughnut2.csv", True),
        (DPATH_TEST_DATA / "doughnut3-invalid.csv", False),
        (DPATH_TEST_DATA / "doughnut4-invalid.csv", False),
    ],
)
def test_validate(fpath, is_valid):
    df_doughnut = Doughnut.load(fpath, validate=False)
    with pytest.raises(ValueError) if not is_valid else nullcontext():
        assert isinstance(Doughnut.validate(df_doughnut), Doughnut)


@pytest.mark.parametrize(
    "status_col,participant,session,expected_count",
    [
        ("downloaded", None, None, 3),
        ("organized", None, None, 2),
        ("converted", None, None, 1),
        ("downloaded", "01", None, 2),
        ("organized", None, "ses-M12", 0),
        ("converted", "01", "ses-BL", 1),
    ],
)
def test_get_participant_sessions_helper(
    status_col, participant, session, expected_count
):
    data = {
        "participant_id": ["01", "01", "02", "02"],
        "visit": ["BL", "M12", "BL", "M12"],
        "session": ["ses-BL", "ses-M12", "ses-BL", "ses-M12"],
        "datatype": ["anat", "anat", "anat", "anat"],
        "participant_dicom_dir": ["01", "01", "02", "02"],
        "dicom_id": ["01", "01", "02", "02"],
        "bids_id": ["01", "01", "02", "02"],
        "downloaded": [True, True, True, False],
        "organized": [True, False, True, False],
        "converted": [True, False, False, False],
    }
    doughnut = Doughnut(data)
    count = 0
    for participant, session in doughnut._get_participant_sessions_helper(
        status_col=status_col, participant=participant, session=session
    ):
        count += 1
    assert count == expected_count


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
