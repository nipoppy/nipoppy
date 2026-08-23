"""Tests for the utils.json5 module."""

from pathlib import Path

import json5
import pytest

from nipoppy.utils.json5 import (
    _find_member_by_key_path,
    _find_root_object_span,
    _parse_object_members,
    _parse_one_member,
    _read_member_key,
    _resolve_child_span,
    _Scanner,
    update_json5_file,
    update_json5_text,
)


def test_update_json5_text_inserts_nested_pipeline_variables():
    text = """
{
  "PIPELINE_VARIABLES": {
    // keep this comment
    "PROCESSING": {},
  }
}
""".strip()

    updated_text = update_json5_text(
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


def test_update_json5_text_inserts_multiple_members_into_new_object():
    # Regression test: inserting a second member into a freshly-created
    # object must not leave a dangling comma on its own line, and must not
    # glue the closing bracket onto the previous member's line.
    text = """
{
    "PIPELINE_VARIABLES": {
        "PROCESSING": {}
    }
}
""".strip()

    expected_text = """
{
    "PIPELINE_VARIABLES": {
        "PROCESSING": {
            "fmriprep": {
                "25.0.0": {
                    "FREESURFER_LICENSE_FILE": null,
                    "TEMPLATEFLOW_HOME": null
                }
            }
        }
    }
}
""".strip()

    updated_text = update_json5_text(
        text,
        [
            (
                [
                    "PIPELINE_VARIABLES",
                    "PROCESSING",
                    "fmriprep",
                    "25.0.0",
                    "FREESURFER_LICENSE_FILE",
                ],
                None,
            ),
            (
                [
                    "PIPELINE_VARIABLES",
                    "PROCESSING",
                    "fmriprep",
                    "25.0.0",
                    "TEMPLATEFLOW_HOME",
                ],
                None,
            ),
        ],
    )

    assert json5.loads(updated_text)["PIPELINE_VARIABLES"]["PROCESSING"] == {
        "fmriprep": {
            "25.0.0": {
                "FREESURFER_LICENSE_FILE": None,
                "TEMPLATEFLOW_HOME": None,
            }
        }
    }
    assert updated_text == expected_text


def test_update_json5_text_replaces_non_object_with_object_for_nested_path():
    text = '{"A": 123}'
    updated_text = update_json5_text(text, [(["A", "B"], "x")])
    assert json5.loads(updated_text) == {"A": {"B": "x"}}


def test_update_json5_text_inserts_inline_into_single_line_object():
    text = '{"A": 1}'
    updated_text = update_json5_text(text, [(["B"], 2)])
    assert updated_text == '{"A": 1, "B": 2}'


def test_update_json5_text_expands_empty_object_to_multiline():
    text = '{"X": {}}'
    updated_text = update_json5_text(text, [(["X", "B"], 2)])
    assert updated_text == '{"X": {\n    "B": 2\n}}'


def test_update_json5_text_inserts_inline_into_nested_single_line_object():
    text = """
{
  "X": {"A": 1}
}
""".strip()
    updated_text = update_json5_text(text, [(["X", "B"], 2)])
    assert updated_text == """
{
  "X": {"A": 1, "B": 2}
}
""".strip()


def test_update_json5_text_inserts_inline_after_member_with_trailing_comma():
    text = '{"A": 1,}'
    updated_text = update_json5_text(text, [(["B"], 2)])
    assert updated_text == '{"A": 1, "B": 2}'


def test_update_json5_text_inserts_into_multiline_empty_object():
    text = """
{
  "X": {
  }
}
""".strip()
    updated_text = update_json5_text(text, [(["X", "B"], 2)])
    assert updated_text == """
{
  "X": {
      "B": 2
  }
}
""".strip()


def test_update_json5_text_raises_on_empty_key_path():
    with pytest.raises(ValueError, match="Key path cannot be empty"):
        update_json5_text('{"A": 1}', [([], "x")])


def test_update_json5_text_raises_on_invalid_json5():
    with pytest.raises(ValueError):
        update_json5_text('{"A": [1, }', [(["A"], 2)])


def test_update_json5_file(tmp_path: Path):
    fpath = tmp_path / "config.json"
    fpath.write_text("""
{
  // keep this comment
  "A": 1,
}
""".strip())

    update_json5_file(fpath, [(["A"], 2), (["B"], True)])

    updated_text = fpath.read_text()
    assert "// keep this comment" in updated_text
    assert json5.loads(updated_text) == {"A": 2, "B": True}


# ---------------------------------------------------------------------------
# Coverage: defensive guards in private helpers. These are not reachable
# through the validated public API (json5.loads rejects malformed input
# before any of these guards would trigger), so they are unit-tested
# directly against the private helpers.
# ---------------------------------------------------------------------------


def test_scanner_find_string_end_index_raises_when_not_on_quote():
    scanner = _Scanner("abc")
    with pytest.raises(ValueError, match="Expected a quoted string"):
        scanner.find_string_end_index()


def test_scanner_find_string_end_index_raises_on_unterminated_string():
    scanner = _Scanner('"abc')
    with pytest.raises(ValueError, match="Unterminated string"):
        scanner.find_string_end_index()


def test_scanner_find_matching_close_bracket_raises_when_not_on_open_char():
    scanner = _Scanner("abc")
    with pytest.raises(ValueError) as exc_info:
        scanner.find_matching_close_bracket("{", "}")
    assert "Expected '{' at index 0" in str(exc_info.value)


def test_scanner_find_matching_close_bracket_raises_when_unterminated():
    scanner = _Scanner("{abc")
    with pytest.raises(ValueError) as exc_info:
        scanner.find_matching_close_bracket("{", "}")
    assert "Could not find matching }" in str(exc_info.value)


def test_scanner_find_value_end_index_raises_at_end_of_input():
    scanner = _Scanner("")
    with pytest.raises(ValueError, match="Expected value, reached end of input"):
        scanner.find_value_end_index()


def test_scanner_skip_whitespace_and_comments_raises_on_unterminated_block_comment():
    scanner = _Scanner("/* unterminated")
    with pytest.raises(ValueError, match="Unterminated block comment"):
        scanner.skip_whitespace_and_comments()


def test_parse_object_members_raises_on_invalid_bounds():
    with pytest.raises(ValueError, match="Object bounds are invalid"):
        _parse_object_members("[1, 2]", 0, 6)


def test_parse_one_member_raises_when_colon_is_missing():
    scanner = _Scanner('"key" 5')
    with pytest.raises(ValueError, match="Expected ':' after key key"):
        _parse_one_member(scanner, len(scanner.text))


def test_read_member_key_raises_when_no_valid_key_at_cursor():
    scanner = _Scanner(": 1")
    with pytest.raises(ValueError, match="Expected an object key at index 0"):
        _read_member_key(scanner)


def test_find_root_object_span_raises_when_top_level_is_not_an_object():
    with pytest.raises(ValueError, match="Expected a top-level object"):
        _find_root_object_span("[1, 2, 3]")


def test_find_member_by_key_path_returns_none_for_missing_key():
    assert _find_member_by_key_path('{"A": 1}', ["MISSING"]) is None


def test_find_member_by_key_path_returns_none_for_non_object_intermediate():
    assert _find_member_by_key_path('{"A": 1}', ["A", "B"]) is None


def test_resolve_child_span_raises_when_key_not_found_after_edit():
    with pytest.raises(ValueError, match="Could not find key after edit: MISSING"):
        _resolve_child_span('{"A": 1}', [], "MISSING")
