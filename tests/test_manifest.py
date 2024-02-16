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
    df_manifest = Manifest.load(fpath, validate=False)
    with pytest.raises(ValueError) if not is_valid else nullcontext():
        assert isinstance(Manifest.validate(df_manifest), Manifest)