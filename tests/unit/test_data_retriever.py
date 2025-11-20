"""Tests for NipoppyDataRetriever class."""

from pathlib import Path

import pandas as pd
import pytest
import pytest_mock

from nipoppy._data_retriever import (
    NipoppyDataRetriever,
    _check_derivatives_arg,
    _check_phenotypes_arg,
)
from nipoppy.tabular.manifest import Manifest


@pytest.fixture
def api(tmp_path: Path) -> NipoppyDataRetriever:
    dpath_root = tmp_path / "my_study"
    return NipoppyDataRetriever(path=dpath_root)


@pytest.mark.parametrize(
    "phenotypes",
    [
        ["nb:Age"],
        ["nb:Age", "nb:Sex"],
    ],
)
def test_check_phenotypes_arg_valid(phenotypes):
    _check_phenotypes_arg(phenotypes)


@pytest.mark.parametrize(
    "phenotypes,error_type,error_message",
    [
        (None, TypeError, "phenotypes must be a list, got"),
        ([], ValueError, "phenotypes list cannot be empty"),
        ([123], TypeError, "Phenotype must be a string, got"),
    ],
)
def test_check_phenotypes_arg_invalid(phenotypes, error_type, error_message):
    with pytest.raises(error_type, match=error_message):
        _check_phenotypes_arg(phenotypes)


@pytest.mark.parametrize(
    "derivatives",
    [
        [("pipeline1", "v1.0", "*/*/pattern1")],
        [("pipeline1", "v1.0", "*/*/pattern1"), ("pipeline1", "v2.0", "pattern1")],
    ],
)
def test_check_derivatives_arg_valid(derivatives):
    _check_derivatives_arg(derivatives)


@pytest.mark.parametrize(
    "derivatives,error_type,error_message",
    [
        (None, TypeError, "derivatives must be a list of tuples, got"),
        ([], ValueError, "derivatives list cannot be empty"),
        (
            ["pipeline1"],
            TypeError,
            ".* must be a tuple containing 3 strings",
        ),
        ([("pipeline1", "v1.0")], TypeError, ".* must be a tuple containing 3 strings"),
        (
            [("pipeline1", "v1.0", 123)],
            TypeError,
            ".* must be a tuple containing 3 strings",
        ),
    ],
)
def test_check_derivatives_arg_invalid(derivatives, error_type, error_message):
    with pytest.raises(error_type, match=error_message):
        _check_derivatives_arg(derivatives)


def test_load_tsv(api: NipoppyDataRetriever, tmp_path: Path):
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


def test_load_tsv_index(api: NipoppyDataRetriever, tmp_path: Path):
    fpath = tmp_path / "test.tsv"
    df_orig = pd.DataFrame(
        {
            "nb:ParticipantID": ["sub-01", "01", "sub-02"],
            "nb:SessionID": ["ses-A", "ses-B", "A"],
            "col1": [1, 2, 3],
        }
    )

    index_cols = ["nb:ParticipantID", "nb:SessionID"]
    df_orig = df_orig.set_index(index_cols)
    df_orig.to_csv(fpath, sep="\t", index=True)

    df_loaded = api._load_tsv(fpath=fpath, index_cols=index_cols)
    assert df_loaded.index.equals(
        pd.MultiIndex.from_tuples(
            [("01", "A"), ("01", "B"), ("02", "A")], names=api._index_cols_output
        )
    )


def test_find_derivatives_path_valid(api: NipoppyDataRetriever):
    pipeline_name = "pipeline1"
    pipeline_version = "v1.0"
    filepath_pattern = "**/idp.tsv"

    # setup
    expected_path = api._study.layout.dpath_root.joinpath(
        "derivatives", pipeline_name, pipeline_version, "idp", "idp.tsv"
    )
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.touch()

    output_path = api._find_derivatives_path(
        pipeline_name, pipeline_version, filepath_pattern
    )
    assert output_path == expected_path


@pytest.mark.parametrize(
    "filepath_pattern,error_type,error_message",
    [
        ("abc.tsv", FileNotFoundError, "No file matching"),
        ("**/idp.tsv", ValueError, "Found more than one file matching"),
    ],
)
def test_find_derivatives_path_invalid(
    api: NipoppyDataRetriever, filepath_pattern, error_type, error_message
):
    pipeline_name = "pipeline1"
    pipeline_version = "v1.0"

    # setup
    for filepath in ("test1/test2/idp.tsv", "test3/idp.tsv"):
        expected_path = (
            Path(api._study.layout.dpath_root)
            / "derivatives"
            / pipeline_name
            / pipeline_version
            / filepath
        )
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.touch()

    with pytest.raises(error_type, match=error_message):
        api._get_derivatives_table(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            filepath_pattern=filepath_pattern,
        )


def test_get_derivatives_table(
    api: NipoppyDataRetriever, mocker: pytest_mock.MockFixture
):
    pipeline_name = "pipeline1"
    pipeline_version = "v1.0"
    filepath_pattern = "**/idp.tsv"

    expected_path = api._study.layout.dpath_root.joinpath(
        "derivatives", pipeline_name, pipeline_version, "test1/test2/idp.tsv"
    )
    mocked_find_derivatives_path = mocker.patch.object(
        api,
        "_find_derivatives_path",
        return_value=expected_path,
    )
    mocked_load_tsv = mocker.patch(
        "nipoppy._data_retriever.NipoppyDataRetriever._load_tsv",
        return_value=pd.DataFrame(),
    )

    df_derivatives = api._get_derivatives_table(
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        filepath_pattern=filepath_pattern,
    )

    mocked_find_derivatives_path.assert_called_once_with(
        pipeline_name, pipeline_version, filepath_pattern
    )
    mocked_load_tsv.assert_called_once_with(
        expected_path, index_cols=api._index_cols_derivatives
    )
    assert df_derivatives.equals(mocked_load_tsv.return_value)


def test_filter_with_manifest(api: NipoppyDataRetriever):
    api._study.manifest = Manifest().add_or_update_records(
        [
            {
                "participant_id": "01",
                "visit_id": "A",
                "session_id": "A",
                "datatype": None,
            },
            {
                "participant_id": "01",
                "visit_id": "C",
                "session_id": "C",
                "datatype": None,
            },
        ]
    )

    df = pd.DataFrame(
        {
            "participant_id": ["01", "01", "01", "02", "02"],
            "session_id": ["A", "B", "C", "A", "B"],
            "col1": [1, 2, 3, 4, 5],
        }
    ).set_index(["participant_id", "session_id"])
    df_expected = pd.DataFrame(
        {
            "participant_id": ["01", "01"],
            "session_id": ["A", "C"],
            "col1": [1, 3],
        }
    ).set_index(["participant_id", "session_id"])

    assert api._filter_with_manifest(df).equals(df_expected)


def test_get_phenotypes(api: NipoppyDataRetriever, mocker: pytest_mock.MockFixture):
    df_harmonized = pd.DataFrame(
        {
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
            "col3": [7, 8, 9],
        },
        index=pd.MultiIndex.from_tuples(
            [("01", "A"), ("01", "B"), ("02", "A")],
            names=["nb:ParticipantID", "nb:SessionID"],
        ),
    )

    mocked_check_phenotypes_arg = mocker.patch(
        "nipoppy._data_retriever._check_phenotypes_arg"
    )
    mocked_load_tsv = mocker.patch.object(
        api,
        "_load_tsv",
        return_value=df_harmonized,
    )
    mocked_filter_with_manifest = mocker.patch.object(
        api,
        "_filter_with_manifest",
        return_value=df_harmonized,
    )

    phenotypes = ["col1", "col3"]
    df_phenotypes = api.get_phenotypes(phenotypes=phenotypes)

    mocked_check_phenotypes_arg.assert_called_once_with(phenotypes)
    mocked_load_tsv.assert_called_once_with(
        api._study.layout.fpath_harmonized, index_cols=api._index_cols_phenotypes
    )
    mocked_filter_with_manifest.assert_called_once_with(df_harmonized)

    assert list(df_phenotypes.columns) == phenotypes


def test_get_derivatives(api: NipoppyDataRetriever, mocker: pytest_mock.MockFixture):
    mocked_check_derivatives_arg = mocker.patch(
        "nipoppy._data_retriever._check_derivatives_arg"
    )
    mocked_get_derivatives_table = mocker.patch.object(
        api,
        "_get_derivatives_table",
        # return string instead of df for testing purposes
        side_effect=(lambda name, version, pattern: f"df_{pattern}"),
    )
    mocked_pd_concat = mocker.patch("pandas.concat", return_value=pd.DataFrame())
    mocked_filter_with_manifest = mocker.patch.object(
        api, "_filter_with_manifest", return_value=pd.DataFrame()
    )

    derivatives = [
        ("pipeline1", "v1.0", "pattern1"),
        ("pipeline2", "v2.0", "pattern2"),
    ]
    df_derivatives = api.get_derivatives(derivatives=derivatives)

    mocked_check_derivatives_arg.assert_called_once_with(derivatives)
    assert mocked_get_derivatives_table.call_count == len(derivatives)
    for derivative_spec in derivatives:
        mocked_get_derivatives_table.assert_any_call(*derivative_spec)
    mocked_pd_concat.assert_called_once_with(
        ["df_pattern1", "df_pattern2"], axis="columns", join="outer"
    )
    assert id(mocked_filter_with_manifest.call_args[0][0]) == id(
        mocked_pd_concat.return_value
    )
    assert id(df_derivatives) == id(mocked_filter_with_manifest.return_value)


def test_get_tabular_data(api: NipoppyDataRetriever, mocker: pytest_mock.MockFixture):
    mocked_get_phenotypes_table = mocker.patch.object(
        api, "get_phenotypes", return_value="df_phenotypes"
    )
    mocked_get_derivatives_table = mocker.patch.object(
        api, "get_derivatives", return_value="df_derivatives"
    )
    mocked_pd_concat = mocker.patch("pandas.concat", return_value=pd.DataFrame())

    phenotypes = ["nb:Age"]
    derivatives = [
        ("pipeline1", "v1.0", "pattern1"),
        ("pipeline2", "v2.0", "pattern2"),
    ]
    df_tabular = api.get_tabular_data(phenotypes=phenotypes, derivatives=derivatives)

    mocked_get_phenotypes_table.assert_called_once_with(phenotypes)
    mocked_get_derivatives_table.assert_called_once_with(derivatives)
    mocked_pd_concat.assert_called_once_with(
        ["df_phenotypes", "df_derivatives"], axis="columns", join="outer"
    )
    assert id(df_tabular) == id(mocked_pd_concat.return_value)


@pytest.mark.parametrize(
    "phenotypes,derivatives,get_phenotypes_called,get_derivatives_called",
    [
        (["nb:Age"], None, True, False),
        (
            None,
            [("pipeline1", "v1.0", "pattern1")],
            False,
            True,
        ),
    ],
)
def test_get_tabular_data_optional_args(
    phenotypes,
    derivatives,
    get_phenotypes_called,
    get_derivatives_called,
    api: NipoppyDataRetriever,
    mocker: pytest_mock.MockFixture,
):
    mocked_get_phenotypes_table = mocker.patch.object(api, "get_phenotypes")
    mocked_get_derivatives_table = mocker.patch.object(api, "get_derivatives")
    mocker.patch("pandas.concat")

    api.get_tabular_data(phenotypes=phenotypes, derivatives=derivatives)

    if get_phenotypes_called:
        mocked_get_phenotypes_table.assert_called_once_with(phenotypes)
    if get_derivatives_called:
        mocked_get_derivatives_table.assert_called_once_with(derivatives)


def test_get_tabular_data_error_no_measures_requested(api: NipoppyDataRetriever):
    with pytest.raises(ValueError, match="Must request at least one measure"):
        api.get_tabular_data(phenotypes=None, derivatives=None)
