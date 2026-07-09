"""Utilities to edit JSON5 objects while preserving comments.

Overview
--------
This module applies targeted edits to JSON5 text *without* reformatting
it, so comments and existing layout survive. It never rebuilds the document
from a parsed tree. Instead it works in two phases:

1. **Locate** the source span (start/end character indices) of the object,
   member, or value that an edit targets.
2. **Splice** new text into that span, leaving everything else byte-for-byte
   unchanged.

The code is organized in layers, from lowest to highest level:

- ``_Scanner``: a cursor over the source text. Each method performs a single
  scanning job (skip trivia, find a string end, match a bracket, find a value
  end) and advances the cursor in place.
- ``_parse_object_members`` / ``_find_root_object_span``: structural parsing
  that produces :class:`_ObjectMember` spans.
- Editing primitives (``_get_line_indent``, ``_format_member_text``,
  ``_insert_member_into_object``): build and splice new member text.
- Navigation helpers (``_find_member_by_key``, ``_get_object_value_span``) and
  the high-level setter (``_set_value_at_key_path``) that resolves a key path
  and writes a value.
- Public API: :func:`update_json5_text` and :func:`update_json5_file`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import json5

from nipoppy.env import StrOrPathLike


@dataclass
class _ObjectMember:
    key: str
    key_start: int
    key_end: int
    value_start: int
    value_end: int
    member_start: int
    member_end: int
    has_comma: bool


_IDENTIFIER_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_WHITESPACE = " \t\r\n"
_VALUE_DELIMITERS = ",}]"


class _Scanner:
    """A forward-only cursor over JSON5 source text.

    The scanner owns the current position (``pos``) so callers never thread a
    character index manually. Each method performs a single scanning job and
    advances ``pos`` past whatever it consumed.

    Parameters
    ----------
    text : str
        Source JSON5 text being scanned.
    pos : int, optional
        Initial cursor position. Defaults to ``0``.
    """

    def __init__(self, text: str, pos: int = 0) -> None:
        self.text = text
        self.pos = pos

    def skip_whitespace_and_comments(self) -> None:
        """Advance the cursor past whitespace and ``//`` / ``/* */`` comments.

        Leaves ``pos`` at the first significant character, or at ``len(text)``.
        This is the only place whitespace and comment syntax is interpreted.
        """
        text = self.text
        n = len(text)
        while self.pos < n:
            ch = text[self.pos]
            if ch in _WHITESPACE:
                self.pos += 1
            elif text.startswith("//", self.pos):
                self._skip_line_comment()
            elif text.startswith("/*", self.pos):
                self._skip_block_comment()
            else:
                return

    def _skip_line_comment(self) -> None:
        """Advance past a ``//`` comment up to (not past) the newline."""
        newline = self.text.find("\n", self.pos + 2)
        self.pos = len(self.text) if newline == -1 else newline

    def _skip_block_comment(self) -> None:
        """Advance past a ``/* ... */`` comment.

        Raises
        ------
        ValueError
            If the block comment is not terminated.
        """
        end = self.text.find("*/", self.pos + 2)
        if end == -1:
            raise ValueError("Unterminated block comment")
        self.pos = end + 2

    def find_string_end_index(self) -> int:
        """Advance past a quoted string and return the index after it.

        Locates the string bounds only; it does not decode the value.

        Raises
        ------
        ValueError
            If the cursor is not on a quote or the string is unterminated.
        """
        text = self.text
        quote = text[self.pos]
        if quote not in ('"', "'"):
            raise ValueError("Expected a quoted string")
        i = self.pos + 1
        while i < len(text):
            # Prevent \\" or \\' from being mistaken for the string end.
            if text[i] == "\\":
                i += 2
                continue
            if text[i] == quote:
                self.pos = i + 1
                return self.pos
            i += 1
        raise ValueError("Unterminated string")

    def find_matching_close_bracket(self, open_ch: str, close_ch: str) -> int:
        """Find the close bracket matching the open bracket under the cursor.

        Returns the index of the matching ``close_ch`` and leaves the cursor on
        it.

        Parameters
        ----------
        open_ch, close_ch : str
            Matching bracket pair, e.g. ``{`` and ``}`` or ``[`` and ``]``.

        Raises
        ------
        ValueError
            If the cursor is not on ``open_ch`` or no matching closing bracket is found.
        """
        text = self.text
        if text[self.pos] != open_ch:
            raise ValueError(f"Expected '{open_ch}' at index {self.pos}")
        depth = 1
        self.pos += 1
        while self.pos < len(text):
            ch = text[self.pos]
            # Skip strings and comments so brackets inside them are ignored.
            if ch in ('"', "'"):
                self.find_string_end_index()
                continue
            if text.startswith("//", self.pos) or text.startswith("/*", self.pos):
                self.skip_whitespace_and_comments()
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return self.pos
            self.pos += 1
        raise ValueError(f"Could not find matching {close_ch}")

    def find_value_end_index(self) -> int:
        """Return the end index (exclusive) of the value under the cursor.

        Dispatches by value kind; primitives are delegated to
        :meth:`_find_primitive_end`.

        Raises
        ------
        ValueError
            If the cursor is at end of input.
        """
        text = self.text
        if self.pos >= len(text):
            raise ValueError("Expected value, reached end of input")
        ch = text[self.pos]
        if ch == "{":
            return self.find_matching_close_bracket("{", "}") + 1
        elif ch == "[":
            return self.find_matching_close_bracket("[", "]") + 1
        elif ch in ('"', "'"):
            return self.find_string_end_index()
        else:
            return self._find_primitive_end()

    def _find_primitive_end(self) -> int:
        """Return the end index (exclusive) of a primitive value.

        A primitive ends at the next delimiter (``,``, ``}``, ``]``) or comment,
        with trailing whitespace excluded.
        """
        text = self.text
        start = self.pos
        i = start
        # Scan forward until the primitive is terminated. A primitive has no
        # explicit closing token, so it runs until the next structural
        # delimiter (',', '}', ']') or the start of a comment, both of which
        # belong to the surrounding document rather than the value itself.
        while i < len(text):
            if text.startswith("//", i) or text.startswith("/*", i):
                break
            if text[i] in _VALUE_DELIMITERS:
                break
            i += 1
        # Walk back over trailing whitespace so the returned span covers only
        # the value; the gap before the delimiter/comment is layout, not part
        # of the primitive, and must be preserved unchanged on edits.
        while i > start and text[i - 1] in _WHITESPACE:
            i -= 1
        return i


# ---------------------------------------------------------------------------
# Structural parsing
# ---------------------------------------------------------------------------


def _parse_object_members(
    text: str,
    obj_start: int,
    obj_end: int,
) -> list[_ObjectMember]:
    """Parse the direct members of an object span into span metadata.

    Key and value spans are captured so edits can target a single member while
    preserving surrounding comments and formatting.

    Parameters
    ----------
    obj_start : int
        Index of the opening ``{``.
    obj_end : int
        End index (exclusive), where ``text[obj_end - 1]`` is ``}``.

    Raises
    ------
    ValueError
        If the object bounds are invalid.
    """
    if text[obj_start] != "{" or text[obj_end - 1] != "}":
        raise ValueError("Object bounds are invalid")

    members: list[_ObjectMember] = []
    scanner = _Scanner(text, obj_start + 1)
    content_end = obj_end - 1

    while True:
        scanner.skip_whitespace_and_comments()
        if scanner.pos >= content_end or text[scanner.pos] == "}":
            break
        members.append(_parse_one_member(scanner, content_end))

    return members


def _parse_one_member(scanner: _Scanner, content_end: int) -> _ObjectMember:
    """Parse the ``key: value`` member at the cursor into span metadata.

    Leaves the cursor just past the member's trailing comma (if any).
    ``content_end`` is the index of the object's closing ``}``.

    Raises
    ------
    ValueError
        If the key or the ``:`` separator is missing.
    """
    member_start = scanner.pos
    key, key_start, key_end = _read_member_key(scanner)

    scanner.skip_whitespace_and_comments()
    if scanner.pos >= len(scanner.text) or scanner.text[scanner.pos] != ":":
        raise ValueError(f"Expected ':' after key {key}")
    scanner.pos += 1

    scanner.skip_whitespace_and_comments()
    value_start = scanner.pos
    value_end = scanner.find_value_end_index()

    scanner.pos = value_end
    scanner.skip_whitespace_and_comments()
    has_comma = scanner.pos < content_end and scanner.text[scanner.pos] == ","
    if has_comma:
        scanner.pos += 1

    return _ObjectMember(
        key=key,
        key_start=key_start,
        key_end=key_end,
        value_start=value_start,
        value_end=value_end,
        member_start=member_start,
        member_end=scanner.pos,
        has_comma=has_comma,
    )


def _read_member_key(scanner: _Scanner) -> tuple[str, int, int]:
    """Read the object key (quoted string or bare identifier) at the cursor.

    Returns ``(key, key_start, key_end)`` and leaves the cursor past the key.

    Raises
    ------
    ValueError
        If no valid key is found at the cursor.
    """
    text = scanner.text
    key_start = scanner.pos
    if text[scanner.pos] in ('"', "'"):
        key_end = scanner.find_string_end_index()
        key = json5.loads(text[key_start:key_end])
        return key, key_start, key_end

    match = _IDENTIFIER_RE.match(text, scanner.pos)
    if match is None:
        raise ValueError(f"Expected an object key at index {scanner.pos}")
    scanner.pos = match.end()
    return match.group(0), key_start, scanner.pos


def _find_root_object_span(text: str) -> tuple[int, int]:
    """Return the ``(start, end)`` span of the top-level object.

    ``start`` is the index of ``{`` and ``end`` is exclusive.

    Raises
    ------
    ValueError
        If the top-level value is not an object.
    """
    scanner = _Scanner(text)
    scanner.skip_whitespace_and_comments()
    if scanner.pos >= len(text) or text[scanner.pos] != "{":
        raise ValueError("Expected a top-level object")
    start = scanner.pos
    end = scanner.find_matching_close_bracket("{", "}")
    return start, end + 1


# ---------------------------------------------------------------------------
# Editing primitives
# ---------------------------------------------------------------------------


def _get_line_indent(text: str, idx: int) -> str:
    """Return the leading whitespace of the line containing ``idx``."""
    line_start = text.rfind("\n", 0, idx) + 1
    i = line_start
    while i < len(text) and text[i] in " \t":
        i += 1
    return text[line_start:i]


def _format_member_text(key: str, value: Any, indent: str) -> str:
    """Render an indented ``"key": value`` snippet (no newline or comma)."""
    return f"{indent}{json.dumps(key)}: {json.dumps(value)}"


def _insert_member_into_object(
    text: str,
    obj_start: int,
    obj_end: int,
    members: list[_ObjectMember],
    key: str,
    value: Any,
) -> str:
    """Insert ``key``/``value`` into an object span and return the new text.

    If the object is non-empty and written on a single line, the new member
    is inserted inline (``{"A": 1, "B": 2}``); otherwise (including when the
    object is initially empty) it is inserted on its own line, with
    indentation inferred from existing ``members`` (or the object's own
    line), and the existing trailing-comma style is preserved.

    Parameters
    ----------
    obj_start : int
        Index of the object's opening ``{``.
    obj_end : int
        Object end index (exclusive).
    """
    is_inline = "\n" not in text[obj_start:obj_end]

    if not members:
        # An initially empty object always expands to multiple lines, even
        # if it was written inline as "{}", so it reads like a normal
        # populated object rather than staying oddly condensed.
        base_indent = _get_line_indent(text, obj_start)
        member_text = _format_member_text(key, value, base_indent + "    ")
        insertion = f"\n{member_text}\n{base_indent}"
        # A member-less object may still contain a comment before "}", which
        # must be preserved. Only trim the whitespace-only run immediately
        # before "}" (that's the empty-looking gap the insertion replaces);
        # anything before it, such as a comment, is kept as-is.
        content_end = obj_end - 1
        trim_start = content_end
        while trim_start > obj_start + 1 and text[trim_start - 1] in _WHITESPACE:
            trim_start -= 1
        return text[:trim_start] + insertion + text[content_end:]

    last = members[-1]
    if is_inline:
        core = _format_member_text(key, value, "")
        if last.has_comma:
            insert_at = last.member_end
            insertion = f" {core}"
        else:
            insert_at = last.value_end
            insertion = f", {core}"
        return text[:insert_at] + insertion + text[insert_at:]

    base_indent = _get_line_indent(text, obj_start)
    member_indent = (
        _get_line_indent(text, members[0].member_start) or base_indent + "    "
    )
    member_text = _format_member_text(key, value, member_indent)

    if last.has_comma:
        # ``member_end`` already sits right after the comma, so the
        # whitespace/indentation leading up to the closing bracket is
        # untouched and the new member lands on its own line before it.
        insert_at = last.member_end
        insertion = f"\n{member_text}"
    else:
        # Without a trailing comma, ``member_end`` swallows the whitespace
        # between the value and the closing bracket (see
        # ``_parse_one_member``), so inserting there would splice the new
        # member in front of that whitespace and glue the closing bracket to
        # it. Insert right after the value instead, adding the missing
        # comma, and let the original trailing whitespace/indentation carry
        # over to precede the closing bracket unchanged.
        insert_at = last.value_end
        insertion = f",\n{member_text}"
    return text[:insert_at] + insertion + text[insert_at:]


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------


def _find_member_by_key(
    members: list[_ObjectMember],
    key: str,
) -> _ObjectMember | None:
    """Return the member with the given ``key``, or ``None`` if absent."""
    return next((member for member in members if member.key == key), None)


def _get_object_value_span(
    text: str,
    member: _ObjectMember,
) -> tuple[int, int] | None:
    """Return a member value's object span as ``(start, end)``, ``end`` exclusive.

    Returns ``None`` if the value is not an object.
    """
    scanner = _Scanner(text, member.value_start)
    scanner.skip_whitespace_and_comments()
    if scanner.pos >= len(text) or text[scanner.pos] != "{":
        return None
    start = scanner.pos
    end = scanner.find_matching_close_bracket("{", "}")
    return start, end + 1


# ---------------------------------------------------------------------------
# High-level functions
# ---------------------------------------------------------------------------


def _find_member_by_key_path(
    text: str,
    key_path: list[str],
) -> _ObjectMember | None:
    """Resolve a member by traversing ``key_path`` from the root object.

    Returns the terminal member, or ``None`` if any key along the path is
    missing or its value is not an object.
    """
    obj_span = _find_root_object_span(text)
    member: _ObjectMember | None = None

    for key in key_path:
        members = _parse_object_members(text, *obj_span)
        member = _find_member_by_key(members, key)
        if member is None:
            return None
        obj_span = _get_object_value_span(text, member)
        if obj_span is None:
            return None

    return member


def _descend_into_object_member(
    text: str,
    obj_span: tuple[int, int],
    key_path: list[str],
    segment: str,
) -> tuple[str, tuple[int, int]]:
    """Ensure ``segment`` is an object within ``obj_span`` and return its span.

    Returns the possibly-updated text and the child object's ``(start, end)``
    span. The segment is handled by case: a missing key is inserted as an empty
    object, a non-object value is replaced with one, and an existing object is
    descended into unchanged. ``key_path`` is the already-traversed path, used
    to re-resolve the child after an edit.
    """
    members = _parse_object_members(text, *obj_span)
    member = _find_member_by_key(members, segment)

    if member is None:
        text = _insert_member_into_object(text, *obj_span, members, segment, {})
        return text, _resolve_child_span(text, key_path, segment)

    child_span = _get_object_value_span(text, member)
    if child_span is None:
        text = text[: member.value_start] + "{}" + text[member.value_end :]
        return text, _resolve_child_span(text, key_path, segment)
    else:
        return text, child_span


def _resolve_child_span(
    text: str,
    key_path: list[str],
    segment: str,
) -> tuple[int, int]:
    """Re-resolve the ``(start, end)`` span of a child object after an edit.

    Raises
    ------
    ValueError
        If the child member cannot be found.
    """
    member = _find_member_by_key_path(text, key_path + [segment])
    if member is None:
        raise ValueError(f"Could not find key after edit: {segment}")
    span = _get_object_value_span(text, member)
    # _find_member_by_key_path only returns a member whose value it has
    # already confirmed is an object, so span is never None here.
    assert span is not None
    return span


def _resolve_or_create_parent_object(
    text: str,
    parent_key_path: list[str],
) -> tuple[str, tuple[int, int]]:
    """Resolve the parent object's span, creating missing objects en route.

    Returns the possibly-updated text and the parent object's ``(start, end)``
    span. Missing intermediates are created and non-object intermediates are
    replaced with empty objects, so the full path is guaranteed to exist.
    """
    obj_span = _find_root_object_span(text)
    traversed: list[str] = []
    for segment in parent_key_path:
        text, obj_span = _descend_into_object_member(text, obj_span, traversed, segment)
        traversed.append(segment)
    return text, obj_span


def _set_value_at_key_path(
    text: str,
    parent_key_path: list[str],
    key: str,
    value: Any,
) -> str:
    """Set ``key`` to ``value`` under the object at ``parent_key_path``.

    Missing intermediate objects are created. An existing ``key`` has only its
    value replaced; a missing ``key`` is inserted.
    """
    text, obj_span = _resolve_or_create_parent_object(text, parent_key_path)

    members = _parse_object_members(text, *obj_span)
    existing = _find_member_by_key(members, key)
    if existing is None:
        return _insert_member_into_object(text, *obj_span, members, key, value)

    value_text = json.dumps(value)
    return text[: existing.value_start] + value_text + text[existing.value_end :]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def update_json5_text(
    text: str,
    updates: Iterable[tuple[list[str], Any]],
) -> str:
    """Apply updates to JSON5 text while preserving comments and formatting.

    Input and output are validated with ``json5.loads``. Updates are applied in
    order, and each update sees the result of previous edits.

    Parameters
    ----------
    updates : Iterable[tuple[list[str], Any]]
        ``(key_path, value)`` tuples. ``key_path`` is a list of nested keys
        whose final key is set to ``value``.

    Returns
    -------
    str
        Updated JSON5 text.

    Raises
    ------
    ValueError
        If the input or resulting text is invalid JSON5, or a key path is
        empty.
    """
    json5.loads(text)

    updated_text = text
    for key_path, value in updates:
        if len(key_path) == 0:
            raise ValueError("Key path cannot be empty")
        updated_text = _set_value_at_key_path(
            updated_text,
            parent_key_path=key_path[:-1],
            key=key_path[-1],
            value=value,
        )

    json5.loads(updated_text)
    return updated_text


def update_json5_file(
    fpath: StrOrPathLike,
    updates: Iterable[tuple[list[str], Any]],
) -> None:
    """Apply ``(key_path, value)`` updates to a JSON5 file in place.

    Parameters
    ----------
    fpath : StrOrPathLike
        Path to the JSON5 file to update.
    updates : Iterable[tuple[list[str], Any]]
        Key-path updates to apply (see :func:`update_json5_text`).
    """
    file_path = Path(fpath)
    text = file_path.read_text()
    updated_text = update_json5_text(text, updates)
    file_path.write_text(updated_text)
