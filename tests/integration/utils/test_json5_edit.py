"""Tests for the utils.jsonc_edit module."""

import json5

from nipoppy.utils.jsonc_edit import update_jsonc_text
from tests.conftest import DPATH_TEST_DATA


def test_update_jsonc_text_updates_existing_value_and_preserves_comment():
    before = DPATH_TEST_DATA / "json5-before.json5"
    expected_text_after = (DPATH_TEST_DATA / "json5-after.json5").read_text().strip()

    updates = [
        (["NAME"], "new_name"),
        (["Inline Dict", "d"], 4),
        (["Nested Dict", "Inner Array"], ["a", "b", "c"]),
        (["Nested Dict", "Inner String"], "new string"),
        (["Nested Dict", "Inner Dict", "float"], 2.0),
        (["Nested Dict", "Inner Dict", "string"], "bar"),
        (["Nested Dict", "Inner Dict", "bool"], False),
        (["Nested Dict", "Inner Dict", "null"], None),
    ]

    updated_text = update_jsonc_text(before.read_text().strip(), updates)
    assert json5.loads(updated_text) == json5.loads(expected_text_after)
    assert updated_text.strip() == expected_text_after
