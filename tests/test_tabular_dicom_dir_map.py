"""Tests for the DICOM directory map classes."""

import pytest

from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import FPATH_SAMPLE_DICOM_DIR_MAP

from .conftest import DPATH_TEST_DATA


@pytest.mark.parametrize(
    "fpath",
    [
        FPATH_SAMPLE_DICOM_DIR_MAP,
        DPATH_TEST_DATA / "dicom_dir_map1.csv",
        DPATH_TEST_DATA / "dicom_dir_map2.csv",
    ],
)
def test_load(fpath):
    assert isinstance(DicomDirMap.load(fpath), DicomDirMap)


@pytest.mark.parametrize(
    "fname",
    [
        "dicom_dir_map_invalid1.csv",
        "dicom_dir_map_invalid2.csv",
        "dicom_dir_map_invalid3.csv",
        "dicom_dir_map_invalid4.csv",
    ],
)
def test_load_invalid(fname):
    with pytest.raises(ValueError):
        DicomDirMap.load(DPATH_TEST_DATA / fname)


@pytest.mark.parametrize(
    "fpath_dicom_dir_map",
    [
        DPATH_TEST_DATA / "dicom_dir_map1.csv",
        str(DPATH_TEST_DATA / "dicom_dir_map1.csv"),
    ],
)
def test_load_or_generate_load(fpath_dicom_dir_map):
    dicom_dir_map = DicomDirMap.load_or_generate(
        manifest=Manifest(),
        fpath_dicom_dir_map=fpath_dicom_dir_map,
        participant_first=True,
    )
    assert isinstance(dicom_dir_map, DicomDirMap)


@pytest.mark.parametrize(
    "participant_ids,sessions,participant_first,expected",
    [
        (["01", "02"], ["1", "2"], True, ["01/1", "02/2"]),
        (["P01", "P02"], ["BL", "BL"], False, ["BL/P01", "BL/P02"]),
    ],
)
def test_load_or_generate_generate(
    participant_ids, sessions, participant_first, expected
):
    manifest = Manifest(
        data={
            Manifest.col_participant_id: participant_ids,
            Manifest.col_visit_id: sessions,
            Manifest.col_session_id: sessions,
            Manifest.col_datatype: [[] for _ in participant_ids],
        }
    )

    dicom_dir_map = DicomDirMap.load_or_generate(
        manifest=manifest,
        fpath_dicom_dir_map=None,
        participant_first=participant_first,
    )

    assert dicom_dir_map[DicomDirMap.col_participant_dicom_dir].tolist() == expected
