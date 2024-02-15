"""Tests for the manifest."""
from contextlib import nullcontext

import pytest
from conftest import DPATH_TEST_DATA

from nipoppy.models.manifest import Manifest


@pytest.mark.parametrize(
    "path",
    [
        DPATH_TEST_DATA / "manifest1.csv",
        DPATH_TEST_DATA / "manifest2.csv",
    ],
)
@pytest.mark.parametrize("validate", [True, False])
def test_load(path, validate):
    assert isinstance(Manifest.load(path, validate=validate), Manifest)


@pytest.mark.parametrize(
    "path,is_valid",
    [
        (DPATH_TEST_DATA / "manifest1.csv", True),
        (DPATH_TEST_DATA / "manifest2.csv", True),
        (DPATH_TEST_DATA / "manifest3-invalid.csv", False),
        (DPATH_TEST_DATA / "manifest4-invalid.csv", False),
    ],
)
def test_validate(path, is_valid):
    df_manifest = Manifest.load(path, validate=False)
    with pytest.raises(ValueError) if not is_valid else nullcontext():
        assert isinstance(df_manifest._validate(), Manifest)
