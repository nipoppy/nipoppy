"""Tests for the manifest."""

from contextlib import nullcontext

import pytest
from conftest import DPATH_TEST_DATA

from nipoppy.models.manifest import Manifest


@pytest.mark.parametrize(
    "fpath",
    [
        DPATH_TEST_DATA / "manifest1.csv",
        DPATH_TEST_DATA / "manifest2.csv",
    ],
)
@pytest.mark.parametrize("validate", [True, False])
def test_load(fpath, validate):
    assert isinstance(Manifest.load(fpath, validate=validate), Manifest)


@pytest.mark.parametrize(
    "fpath,is_valid",
    [
        (DPATH_TEST_DATA / "manifest1.csv", True),
        (DPATH_TEST_DATA / "manifest2.csv", True),
        (DPATH_TEST_DATA / "manifest3-invalid.csv", False),
        (DPATH_TEST_DATA / "manifest4-invalid.csv", False),
    ],
)
def test_validate(fpath, is_valid):
    manifest = Manifest.load(fpath, validate=False)
    with pytest.raises(ValueError) if not is_valid else nullcontext():
        assert isinstance(Manifest.validate(manifest), Manifest)


@pytest.mark.parametrize(
    "sessions,visits,is_valid",
    [
        (None, None, True),
        (["ses-BL", "ses-M12"], ["BL", "M12"], True),
        (["ses-BL"], ["BL", "M12"], False),
        (["ses-BL", "ses-M12"], ["M12"], False),
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
    "participant_id,session,visit,datatype",
    [
        ("01", "BL", "ses-BL", ["anat"]),
        ("01", "M12", "ses-M12", ["anat"]),
        ("02", "M12", "ses-M12", ["anat", "dwi"]),
    ],
)
def test_add_record(participant_id, visit, session, datatype):
    manifest = Manifest().add_record(
        participant_id=participant_id,
        visit=visit,
        session=session,
        datatype=datatype,
    )
    assert isinstance(manifest, Manifest)
    assert len(manifest) == 1


@pytest.mark.parametrize(
    "data,session,expected_count",
    [
        (
            {
                "participant_id": ["01"],
                "visit": ["BL"],
                "session": [None],
                "datatype": [[]],
            },
            "ses-BL",
            0,
        ),
        (
            {
                "participant_id": ["01"],
                "visit": ["BL"],
                "session": ["ses-BL"],
                "datatype": [["anat"]],
            },
            "ses-BL",
            1,
        ),
        (
            {
                "participant_id": ["01", "02"],
                "visit": ["BL", "M12"],
                "session": ["ses-BL", "ses-M12"],
                "datatype": [["anat"], ["anat", "dwi"]],
            },
            "ses-BL",
            1,
        ),
        (
            {
                "participant_id": ["01", "02"],
                "visit": ["BL", "M12"],
                "session": ["ses-BL", "ses-M12"],
                "datatype": [["anat"], ["anat", "dwi"]],
            },
            None,
            2,
        ),
    ],
)
def test_imaging_only(data, session, expected_count):
    manifest = Manifest(data)
    manifest_with_imaging_only = manifest.get_imaging_only(session=session)
    assert isinstance(manifest_with_imaging_only, Manifest)
    assert len(manifest_with_imaging_only) == expected_count
