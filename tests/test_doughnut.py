"""Tests for the manifest."""

from contextlib import nullcontext

import pytest
from conftest import DPATH_TEST_DATA

from nipoppy.tabular.doughnut import Doughnut


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
