"""Tests for the utils.jsonc_edit module."""

from pathlib import Path

import json5
import pytest

from nipoppy.utils.jsonc_edit import update_jsonc_file, update_jsonc_text


def test_update_jsonc_text_updates_existing_value_and_preserves_comment():
    text = """
{
  // keep this comment
  "NAME": "old_name",
  "VERSION": "1.0.0",
}
""".strip()

    updated_text = update_jsonc_text(text, [(["NAME"], "new_name")])
    assert "// keep this comment" in updated_text
    assert '"NAME": "new_name"' in updated_text
    assert json5.loads(updated_text) == {
        "NAME": "new_name",
        "VERSION": "1.0.0",
    }


def test_update_jsonc_text_inserts_nested_pipeline_variables():
    text = """
{
  "PIPELINE_VARIABLES": {
    // keep this comment
    "PROCESSING": {},
  }
}
""".strip()

    updated_text = update_jsonc_text(
        text,
        [
            (
                [
                    "PIPELINE_VARIABLES",
                    "PROCESSING",
                    "my_pipeline",
                    "1.0.0",
                    "var1",
                ],
                None,
            )
        ],
    )

    assert "// keep this comment" in updated_text
    assert '"var1": null' in updated_text
    assert json5.loads(updated_text)["PIPELINE_VARIABLES"]["PROCESSING"] == {
        "my_pipeline": {"1.0.0": {"var1": None}}
    }


def test_update_jsonc_text_replaces_non_object_with_object_for_nested_path():
    text = '{"A": 123}'
    updated_text = update_jsonc_text(text, [(["A", "B"], "x")])
    assert json5.loads(updated_text) == {"A": {"B": "x"}}


def test_update_jsonc_text_raises_on_empty_path():
    with pytest.raises(ValueError, match="Path cannot be empty"):
        update_jsonc_text('{"A": 1}', [([], "x")])


def test_update_jsonc_text_raises_on_invalid_jsonc():
    with pytest.raises(ValueError):
        update_jsonc_text('{"A": [1, }', [(["A"], 2)])


def test_update_jsonc_file(tmp_path: Path):
    fpath = tmp_path / "config.json"
    fpath.write_text("""
{
  // keep this comment
  "A": 1,
}
""".strip())

    update_jsonc_file(fpath, [(["A"], 2), (["B"], True)])

    updated_text = fpath.read_text()
    assert "// keep this comment" in updated_text
    assert json5.loads(updated_text) == {"A": 2, "B": True}
