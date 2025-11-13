"""Tests for NipoppyDataAPI class."""

from pathlib import Path

import pandas as pd
import pytest
import pytest_mock

from nipoppy.data_api import NipoppyDataAPI
from nipoppy.layout import DatasetLayout
from nipoppy.study import Study
from nipoppy.tabular.manifest import Manifest


@pytest.fixture
def api(tmp_path: Path) -> NipoppyDataAPI:
    dpath_root = tmp_path / "my_study"
    return NipoppyDataAPI(study=Study(layout=DatasetLayout(dpath_root=dpath_root)))


def test_load_tsv(api: NipoppyDataAPI, tmp_path: Path):
    fpath = tmp_path / "test.tsv"
    df_orig = pd.DataFrame(
        {
            "participant_id": ["01", "01", "02"],
            "session_id": ["A", "B", "A"],
            "col1": [1, 2, 3],
        }
    )

    index_cols = ["participant_id", "session_id"]
    df_orig = df_orig.set_index(index_cols)
    df_orig.to_csv(fpath, sep="\t", index=True)

    df_loaded = api._load_tsv(fpath=fpath, index_cols=index_cols)
    assert df_loaded.equals(df_orig)


@pytest.mark.parametrize(
    "derivatives",
    [[], [("pipeline1", "v1.0", "*/*/pattern1"), ("pipeline1", "v2.0", "pattern1")]],
)
def test_check_derivatives_arg_valid(api: NipoppyDataAPI, derivatives):
    api._check_derivatives_arg(derivatives)


@pytest.mark.parametrize(
    "derivatives,error_message",
    [
        (None, "derivatives must be a list of tuples, got"),
        (
            ["pipeline1"],
            ".* must be a tuple containing 3 strings",
        ),
        ([("pipeline1", "v1.0")], ".* must be a tuple containing 3 strings"),
        ([("pipeline1", "v1.0", 123)], ".* must be a tuple containing 3 strings"),
    ],
)
def test_check_derivatives_arg_invalid(api: NipoppyDataAPI, derivatives, error_message):
    with pytest.raises(TypeError, match=error_message):
        api._check_derivatives_arg(derivatives)


def test_get_derivatives_table(
    api: NipoppyDataAPI,
    mocker: pytest_mock.MockFixture,
):
    pipeline_name = "pipeline1"
    pipeline_version = "v1.0"
    filepath_pattern = "**/idp.tsv"

    expected_path = (
        Path(api.study.layout.dpath_root)
        / "derivatives"
        / pipeline_name
        / pipeline_version
        / "test1/test2/idp.tsv"
    )
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.touch()

    mocked = mocker.patch(
        "nipoppy.data_api.NipoppyDataAPI._load_tsv",
        return_value=pd.DataFrame(),
    )

    df_derivatives = api._get_derivatives_table(
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        filepath_pattern=filepath_pattern,
    )
    mocked.assert_called_once_with(expected_path, index_cols=api.imaging_index_cols)
    assert df_derivatives.equals(mocked.return_value)


def test_get_derivatives_table_error_not_found(api: NipoppyDataAPI):

    with pytest.raises(FileNotFoundError, match="No file matching"):
        api._get_derivatives_table(
            pipeline_name="pipeline1",
            pipeline_version="v1.0",
            filepath_pattern="**/idp.tsv",
        )


def test_get_derivatives_table_error_multiple_found(
    api: NipoppyDataAPI,
):
    pipeline_name = "pipeline1"
    pipeline_version = "v1.0"
    filepath_pattern = "**/idp.tsv"

    for filepath in ("test1/test2/idp.tsv", "test3/idp.tsv"):
        expected_path = (
            Path(api.study.layout.dpath_root)
            / "derivatives"
            / pipeline_name
            / pipeline_version
            / filepath
        )
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.touch()

    with pytest.raises(RuntimeError, match="Found more than one file matching"):
        api._get_derivatives_table(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            filepath_pattern=filepath_pattern,
        )


def test_get_tabular_data(api: NipoppyDataAPI, mocker: pytest_mock.MockFixture):
    def _get_dummy_idp_table(pipeline_name, pipeline_version, filepath_pattern):
        return pd.DataFrame(
            {
                "participant_id": ["01", "01", "02"],
                "session_id": ["A", "B", "A"],
                f"{pipeline_name}_{pipeline_version}_{filepath_pattern}": [
                    1.0,
                    2.0,
                    3.0,
                ],
            }
        ).set_index(["participant_id", "session_id"])

    mocked_get_derivatives_table = mocker.patch(
        "nipoppy.data_api.NipoppyDataAPI._get_derivatives_table",
        side_effect=_get_dummy_idp_table,
    )
    api.study.manifest = Manifest().add_or_update_records(
        {
            "participant_id": "01",
            "visit_id": "A",
            "session_id": "A",
            "datatype": None,
        }
    )

    df_tabular = api.get_tabular_data(
        derivatives=[
            ("pipeline1", "v1.0", "pattern1"),
            ("pipeline2", "v2.0", "pattern2"),
        ]
    )

    assert mocked_get_derivatives_table.call_count == 2
    assert len(df_tabular) == len(api.study.manifest)
    assert df_tabular.index.names == api.imaging_index_cols
    assert list(df_tabular.columns) == [
        "pipeline1_v1.0_pattern1",
        "pipeline2_v2.0_pattern2",
    ]
