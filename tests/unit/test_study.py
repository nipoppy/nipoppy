"""Tests for the Study class."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.layout import DatasetLayout
from nipoppy.study import Study
from tests.conftest import get_config


@pytest.fixture
def study(tmp_path: Path):
    dpath_root = tmp_path / "my_study"
    return Study(layout=DatasetLayout(dpath_root=dpath_root))


def test_config(study: Study, mocker: pytest_mock.MockFixture):
    config = get_config(dicom_dir_map_file="[[NIPOPPY_DPATH_ROOT]]")
    mocked_load = mocker.patch("nipoppy.study.Config.load", return_value=config)

    processed_config = study.config

    # test load
    mocked_load.assert_called_once_with(study.layout.fpath_config)

    # test placeholder replacement
    assert str(processed_config.DICOM_DIR_MAP_FILE) == str(study.layout.dpath_root)


@pytest.mark.parametrize(
    "property_name,layout_attribute_name,tabular_class",
    [
        ("manifest", "fpath_manifest", "Manifest"),
        ("curation_status_table", "fpath_curation_status", "CurationStatusTable"),
        ("processing_status_table", "fpath_processing_status", "ProcessingStatusTable"),
    ],
)
def test_tabular_file_load(
    property_name,
    layout_attribute_name,
    tabular_class: str,
    study: Study,
    mocker: pytest_mock.MockFixture,
):
    fpath = study.layout.dpath_root / "tabular_file.tsv"
    mocker.patch.object(study.layout, layout_attribute_name, new=fpath)
    mocked_load = mocker.patch(f"nipoppy.study.{tabular_class}.load")

    # access the property
    getattr(study, property_name)

    mocked_load.assert_called_once_with(fpath)
