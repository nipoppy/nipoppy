"""Tests for the utils module."""

import json
import re
from pathlib import Path

import pandas as pd
import pytest
from conftest import DPATH_TEST_DATA
from fids import fids

from nipoppy.layout import DatasetLayout
from nipoppy.utils import (
    check_participant,
    check_session,
    dicom_id_to_bids_id,
    get_pipeline_tag,
    load_json,
    participant_id_to_bids_id,
    participant_id_to_dicom_id,
    process_template_str,
    save_df_with_backup,
    save_json,
    strip_session,
)


@pytest.mark.parametrize(
    "participant_id,expected",
    [("123", "123"), ("P_123", "P123"), ("sub!@#-", "sub")],
)
def test_participant_id_to_dicom_id(participant_id, expected):
    assert participant_id_to_dicom_id(participant_id) == expected


@pytest.mark.parametrize(
    "dicom_id,expected",
    [("123", "sub-123"), ("P123", "sub-P123"), ("sub", "sub-sub")],
)
def test_dicom_id_to_bids_id(dicom_id, expected):
    assert dicom_id_to_bids_id(dicom_id) == expected


@pytest.mark.parametrize(
    "participant_id,expected",
    [("123", "sub-123"), ("P_123", "sub-P123"), ("sub!@#-", "sub-sub")],
)
def test_participant_id_to_bids_id(participant_id, expected):
    assert participant_id_to_bids_id(participant_id) == expected


@pytest.mark.parametrize(
    "participant,expected",
    [("sub-01", "01"), ("01", "01"), (None, None)],
)
def test_check_participant(participant, expected):
    assert check_participant(participant) == expected


@pytest.mark.parametrize(
    "session,expected",
    [("ses-BL", "ses-BL"), ("BL", "ses-BL"), ("M12", "ses-M12"), (None, None)],
)
def test_check_session(session, expected):
    assert check_session(session) == expected


@pytest.mark.parametrize(
    "session,expected", [("ses-BL", "BL"), ("BL", "BL"), ("ses-01", "01"), (None, None)]
)
def test_strip_session(session, expected):
    assert strip_session(session) == expected


@pytest.mark.parametrize(
    "dpath_bids_db,ignore_patterns,expected_count",
    [
        (None, None, 13),
        ("bids_db", [re.compile("^(?!/sub-(02))")], 9),
        ("bids_db", [re.compile(".*?/ses-(?!3)")], 3),
        ("bids_db", [re.compile("^(?!/sub-(01))"), re.compile(".*?/ses-(?!3)")], 0),
        ("bids_db", [re.compile(".*/anat/")], 3),
        ("bids_db", ["sub-01"], 9),
    ],
)
@pytest.mark.parametrize("resolve_paths", [True, False])
def test_create_bids_db(
    dpath_bids_db, ignore_patterns, expected_count, resolve_paths, tmp_path: Path
):
    from nipoppy.utils import create_bids_db

    dpath_bids = tmp_path / "bids"
    if dpath_bids_db is not None:
        dpath_bids_db: Path = tmp_path / dpath_bids_db

    fids.create_fake_bids_dataset(
        output_dir=dpath_bids, subjects=["01"], sessions=["1", "2"], datatypes=["anat"]
    )
    fids.create_fake_bids_dataset(
        output_dir=dpath_bids,
        subjects=["02"],
        sessions=["1", "2", "3"],
        datatypes=["anat", "func"],
    )

    bids_layout = create_bids_db(
        dpath_bids=dpath_bids,
        dpath_bids_db=dpath_bids_db,
        ignore_patterns=ignore_patterns,
        resolve_paths=resolve_paths,
    )
    assert len(bids_layout.get(extension="nii.gz")) == expected_count
    if dpath_bids_db is not None:
        assert dpath_bids_db.exists()


@pytest.mark.parametrize(
    "name,version,step,participant,session,expected",
    [
        ("my_pipeline", "1.0", None, None, None, "my_pipeline-1.0"),
        ("pipeline", "2.0", None, "3000", None, "pipeline-2.0-3000"),
        ("pipeline", "2.0", None, None, "ses-BL", "pipeline-2.0-BL"),
        ("pipeline", "2.0", "step1", "3000", "BL", "pipeline-2.0-step1-3000-BL"),
    ],
)
def test_get_pipeline_tag(name, version, participant, step, session, expected):
    assert (
        get_pipeline_tag(
            pipeline_name=name,
            pipeline_version=version,
            pipeline_step=step,
            participant=participant,
            session=session,
        )
        == expected
    )


def test_load_json():
    assert isinstance(load_json(DPATH_TEST_DATA / "config1.json"), dict)


def test_save_json(tmp_path: Path):
    json_object = {"a": 1, "b": 2}
    fpath = tmp_path / "test.json"
    save_json(json_object, fpath)
    assert fpath.exists()
    with fpath.open("r") as file:
        assert json.load(file) == json_object


@pytest.mark.parametrize("dname_backups", [None, ".tests"])
@pytest.mark.parametrize(
    "fname,dname_backups_processed",
    [("test.csv", ".tests"), ("test2.csv", ".test2s")],
)
def test_save_df_with_backup(
    fname: str,
    dname_backups: str | None,
    dname_backups_processed: str,
    tmp_path: Path,
):
    fpath_symlink = tmp_path / fname
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    fpath_backup = save_df_with_backup(df, fpath_symlink, dname_backups)

    if dname_backups is None:
        dname_backups = dname_backups_processed

    assert fpath_symlink.exists()
    assert fpath_backup.exists()
    assert fpath_backup.parent == fpath_symlink.parent / dname_backups


@pytest.mark.parametrize(
    "template_str,resolve_paths,objs,kwargs,expected",
    [
        ("no_replace", False, None, {}, "no_replace"),
        (
            "[[NIPOPPY_DPATH_ROOT]]",
            False,
            [DatasetLayout("my_dataset")],
            {},
            "my_dataset",
        ),
        (
            "[[NIPOPPY_SOME_KWARG_PATH]]",
            False,
            [],
            {"some_kwarg_path": Path("a_path")},
            "a_path",
        ),
        (
            "[[NIPOPPY_SOME_KWARG_PATH]]",
            True,
            [],
            {"some_kwarg_path": Path("a_path")},
            str(Path("a_path").resolve()),
        ),
    ],
)
def test_process_template_str(template_str, resolve_paths, objs, kwargs, expected):
    assert (
        process_template_str(
            template_str, resolve_paths=resolve_paths, objs=objs, **kwargs
        )
        == expected
    )


@pytest.mark.parametrize("template_str", ["[[NIPOPPY_123]]", "[[NIPOPPY_-]]"])
def test_process_template_str_error_identifier(template_str):
    with pytest.raises(ValueError, match="Invalid identifier name"):
        process_template_str(template_str)


def test_process_template_str_error_replace():
    with pytest.raises(RuntimeError, match="Unable to replace"):
        process_template_str("[[NIPOPPY_INVALID]]")