"""Tests for links in documentation."""

from pathlib import Path

import httpx
import pytest


@pytest.mark.parametrize(
    "link",
    (
        Path(__file__)
        .parents[2]
        .joinpath("docs/source/ignored_links.txt")
        .read_text()
        .splitlines()
    ),
)
def test_links(link):
    """Test that all links in the documentation are valid."""
    response = httpx.get(link, follow_redirects=True)
    response.raise_for_status()
