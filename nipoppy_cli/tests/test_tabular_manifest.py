"""Tests for the manifest."""

from contextlib import nullcontext

import pandas as pd
import pytest

from nipoppy.tabular.manifest import Manifest

from .conftest import DPATH_TEST_DATA


@pytest.mark.parametrize(
    "fpath",
    [
        DPATH_TEST_DATA / "manifest1.csv",
        DPATH_TEST_DATA / "manifest2.csv",
        DPATH_TEST_DATA / "manifest3.csv",
    ],
)
@pytest.mark.parametrize("validate", [True, False])
def test_load(fpath, validate):
    assert isinstance(Manifest.load(fpath, validate=validate), Manifest)


def test_load_keep_extra_cols():
    fpath = DPATH_TEST_DATA / "manifest3.csv"
    expected_cols = pd.read_csv(fpath).columns
    manifest = Manifest.load(fpath)
    assert set(manifest.columns) == set(expected_cols)
    assert isinstance(manifest.validate(), Manifest)


@pytest.mark.parametrize(
    "fpath,is_valid",
    [
        (DPATH_TEST_DATA / "manifest1.csv", True),
        (DPATH_TEST_DATA / "manifest2.csv", True),
        (DPATH_TEST_DATA / "manifest_invalid1.csv", False),
        (DPATH_TEST_DATA / "manifest_invalid2.csv", False),
        (DPATH_TEST_DATA / "manifest_invalid3.csv", False),
        (DPATH_TEST_DATA / "manifest_invalid4.csv", False),
    ],
)
def test_validate(fpath, is_valid):
    manifest = Manifest.load(fpath, validate=False)
    with pytest.raises(ValueError) if not is_valid else nullcontext():
        assert isinstance(manifest.validate(), Manifest)


@pytest.mark.parametrize(
    "sessions,visits,is_valid",
    [
        (None, None, True),
        (["BL", "M12"], ["BL", "M12"], True),
        (["BL"], ["BL", "M12"], False),
        (["BL", "M12"], ["M12"], False),
    ],
)
def test_validate_sessions_visits(sessions, visits, is_valid):
    manifest = Manifest.load(
        DPATH_TEST_DATA / "manifest1.csv",
        sessions=sessions,
        visits=visits,
        validate=False,
    )
    with pytest.raises(ValueError) if not is_valid else nullcontext():
        assert isinstance(Manifest.validate(manifest), Manifest)


@pytest.mark.parametrize(
    "data,session,expected_count",
    [
        (
            (["01"], ["BL"], None, [[]]),
            "BL",
            0,
        ),
        (
            (["01"], ["BL"], "BL", [["anat"]]),
            "BL",
            1,
        ),
        (
            (
                ["01", "02"],
                ["BL", "M12"],
                ["BL", "M12"],
                [["anat"], ["anat", "dwi"]],
            ),
            "BL",
            1,
        ),
        (
            (
                ["01", "02"],
                ["BL", "M12"],
                ["BL", "M12"],
                [["anat"], ["anat", "dwi"]],
            ),
            None,
            2,
        ),
    ],
)
def test_get_imaging_subset(data, session, expected_count):
    manifest = Manifest(
        {
            Manifest.col_participant_id: data[0],
            Manifest.col_visit: data[1],
            Manifest.col_session: data[2],
            Manifest.col_datatype: data[3],
        }
    )
    manifest_with_imaging_only = manifest.get_imaging_subset(session=session)
    assert isinstance(manifest_with_imaging_only, Manifest)
    assert len(manifest_with_imaging_only) == expected_count


@pytest.mark.parametrize(
    "participant,session,expected_count",
    [
        (None, None, 6),
        ("01", None, 3),
        ("02", None, 2),
        ("03", None, 1),
        (None, "ses-BL", 3),
        (None, "ses-M12", 2),
        (None, "ses-M24", 1),
        ("01", "ses-M24", 1),
        ("02", "ses-M12", 1),
        ("03", "ses-BL", 1),
    ],
)
def get_participants_sessions(participant, session, expected_count):
    data = (
        {
            "participant_id": ["01", "01", "01", "02", "02", "03", "04"],
            "visit": ["BL", "M12", "M24", "BL", "M12", "BL", "SC"],
            "session": [
                "ses-BL",
                "ses-M12",
                "ses-M24",
                "ses-BL",
                "ses-M12",
                "ses-BL",
                None,
            ],
            "datatype": [
                ["anat"],
                ["anat"],
                ["anat"],
                ["anat"],
                ["anat"],
                ["anat"],
                [],
            ],
        },
    )
    manifest = Manifest(data)
    count = 0
    for _ in manifest.get_participants_sessions(
        participant=participant, session=session
    ):
        count += 1
    assert count == expected_count
