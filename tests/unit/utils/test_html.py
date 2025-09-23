"""Tests for the utils.html module."""

import pytest

from nipoppy.utils.html import strip_html_tags


@pytest.mark.parametrize(
    "html,tags,expected",
    [
        ("<div><p>Test</p></div>", None, "Test"),
        ("<div><p>Test</p></div>", {"p"}, "<div>Test</div>"),
    ],
)
def test_strip_html_tags(html, tags, expected):
    assert strip_html_tags(html, tags) == expected
