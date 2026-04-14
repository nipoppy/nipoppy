"""Utilities to edit JSONC/JSON5 objects while preserving comments."""

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


def _skip_ws_and_comments(text: str, idx: int) -> int:
    n = len(text)
    while idx < n:
        ch = text[idx]
        if ch in " \t\r\n":
            idx += 1
            continue
        if text.startswith("//", idx):
            idx += 2
            while idx < n and text[idx] != "\n":
                idx += 1
            continue
        if text.startswith("/*", idx):
            end = text.find("*/", idx + 2)
            if end == -1:
                raise ValueError("Unterminated block comment")
            idx = end + 2
            continue
        return idx
    return idx


def _parse_quoted_string(text: str, idx: int) -> tuple[str, int]:
    quote = text[idx]
    if quote not in ('"', "'"):
        raise ValueError("Expected a quoted string")
    i = idx + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            raw = text[idx : i + 1]
            value = json.loads(raw) if quote == '"' else json5.loads(raw)
            return value, i + 1
        i += 1
    raise ValueError("Unterminated string")


def _find_matching_bracket(text: str, idx: int, open_ch: str, close_ch: str) -> int:
    assert text[idx] == open_ch
    depth = 1
    i = idx + 1
    while i < len(text):
        ch = text[i]
        if ch in ('"', "'"):
            _, i = _parse_quoted_string(text, i)
            continue
        if text.startswith("//", i):
            i = _skip_ws_and_comments(text, i)
            continue
        if text.startswith("/*", i):
            i = _skip_ws_and_comments(text, i)
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"Could not find matching {close_ch}")


def _parse_value_end(text: str, idx: int) -> int:
    if idx >= len(text):
        raise ValueError("Expected value, reached end of input")
    ch = text[idx]
    if ch == "{":
        return _find_matching_bracket(text, idx, "{", "}") + 1
    if ch == "[":
        return _find_matching_bracket(text, idx, "[", "]") + 1
    if ch in ('"', "'"):
        _, end = _parse_quoted_string(text, idx)
        return end

    i = idx
    while i < len(text):
        if text.startswith("//", i) or text.startswith("/*", i):
            break
        if text[i] in ",}]":
            break
        i += 1

    while i > idx and text[i - 1] in " \t\r\n":
        i -= 1
    return i


def _parse_object_members(
    text: str,
    obj_start: int,
    obj_end: int,
) -> list[_ObjectMember]:
    if text[obj_start] != "{" or text[obj_end - 1] != "}":
        raise ValueError("Object bounds are invalid")

    members: list[_ObjectMember] = []
    idx = _skip_ws_and_comments(text, obj_start + 1)

    while idx < obj_end - 1:
        idx = _skip_ws_and_comments(text, idx)
        if idx >= obj_end - 1:
            break
        if text[idx] == "}":
            break

        member_start = idx
        key_start = idx
        if text[idx] in ('"', "'"):
            key, idx = _parse_quoted_string(text, idx)
            key_end = idx
        else:
            match = _IDENTIFIER_RE.match(text, idx)
            if match is None:
                raise ValueError(f"Expected an object key at index {idx}")
            key = match.group(0)
            idx = match.end()
            key_end = idx

        idx = _skip_ws_and_comments(text, idx)
        if idx >= len(text) or text[idx] != ":":
            raise ValueError(f"Expected ':' after key {key}")
        idx += 1

        idx = _skip_ws_and_comments(text, idx)
        value_start = idx
        value_end = _parse_value_end(text, idx)
        idx = _skip_ws_and_comments(text, value_end)

        has_comma = False
        if idx < obj_end - 1 and text[idx] == ",":
            has_comma = True
            idx += 1

        member_end = idx
        members.append(
            _ObjectMember(
                key=key,
                key_start=key_start,
                key_end=key_end,
                value_start=value_start,
                value_end=value_end,
                member_start=member_start,
                member_end=member_end,
                has_comma=has_comma,
            )
        )

    return members


def _find_root_object_span(text: str) -> tuple[int, int]:
    idx = _skip_ws_and_comments(text, 0)
    if idx >= len(text) or text[idx] != "{":
        raise ValueError("Expected a top-level object")
    end = _find_matching_bracket(text, idx, "{", "}")
    return idx, end + 1


def _line_indent(text: str, idx: int) -> str:
    line_start = text.rfind("\n", 0, idx) + 1
    i = line_start
    while i < len(text) and text[i] in " \t":
        i += 1
    return text[line_start:i]


def _insert_member(
    text: str,
    obj_start: int,
    obj_end: int,
    members: list[_ObjectMember],
    key: str,
    value: Any,
) -> str:
    key_text = json.dumps(key)
    value_text = json.dumps(value)
    base_indent = _line_indent(text, obj_start)
    member_indent = _line_indent(text, members[0].member_start) if members else ""
    if not member_indent:
        member_indent = base_indent + "    "

    if not members:
        insertion = f"\n{member_indent}{key_text}: {value_text}\n{base_indent}"
        return text[: obj_start + 1] + insertion + text[obj_start + 1 :]

    last_member = members[-1]
    comma_prefix = "" if last_member.has_comma else ","
    insertion = f"{comma_prefix}\n{member_indent}{key_text}: {value_text}"
    return text[: obj_end - 1] + insertion + text[obj_end - 1 :]


def _find_member_at_path(text: str, path: list[str]) -> _ObjectMember | None:
    obj_start, obj_end = _find_root_object_span(text)
    members = _parse_object_members(text, obj_start, obj_end)
    member: _ObjectMember | None = None

    for key in path:
        member = next((item for item in members if item.key == key), None)
        if member is None:
            return None

        value_idx = _skip_ws_and_comments(text, member.value_start)
        if text[value_idx] != "{":
            return None
        obj_start = value_idx
        obj_end = _find_matching_bracket(text, obj_start, "{", "}") + 1
        members = _parse_object_members(text, obj_start, obj_end)

    return member


def _set_key_in_object(text: str, object_path: list[str], key: str, value: Any) -> str:
    obj_start, obj_end = _find_root_object_span(text)
    traversed_path: list[str] = []

    for segment in object_path:
        members = _parse_object_members(text, obj_start, obj_end)
        member = next((item for item in members if item.key == segment), None)
        if member is None:
            text = _insert_member(text, obj_start, obj_end, members, segment, {})
            member = _find_member_at_path(text, traversed_path + [segment])
            if member is None:
                raise ValueError(f"Could not find newly inserted key: {segment}")
            value_idx = _skip_ws_and_comments(text, member.value_start)
            obj_start = value_idx
            obj_end = _find_matching_bracket(text, obj_start, "{", "}") + 1
            traversed_path.append(segment)
            continue

        value_idx = _skip_ws_and_comments(text, member.value_start)
        if text[value_idx] != "{":
            text = text[: member.value_start] + "{}" + text[member.value_end :]
            parent_member = _find_member_at_path(text, traversed_path + [segment])
            if parent_member is None:
                raise ValueError(f"Could not find updated key: {segment}")
            member = parent_member
            value_idx = _skip_ws_and_comments(text, member.value_start)

        obj_start = value_idx
        obj_end = _find_matching_bracket(text, obj_start, "{", "}") + 1
        traversed_path.append(segment)

    members = _parse_object_members(text, obj_start, obj_end)
    existing_member = next((item for item in members if item.key == key), None)

    if existing_member is None:
        return _insert_member(text, obj_start, obj_end, members, key, value)

    value_text = json.dumps(value)
    return (
        text[: existing_member.value_start]
        + value_text
        + text[existing_member.value_end :]
    )


def update_jsonc_text(
    text: str,
    updates: Iterable[tuple[list[str], Any]],
) -> str:
    """Apply updates to JSONC text while preserving comments and formatting."""
    json5.loads(text)

    updated_text = text
    for path, value in updates:
        if len(path) == 0:
            raise ValueError("Path cannot be empty")
        updated_text = _set_key_in_object(
            updated_text,
            object_path=path[:-1],
            key=path[-1],
            value=value,
        )

    json5.loads(updated_text)
    return updated_text


def update_jsonc_file(
    fpath: StrOrPathLike,
    updates: Iterable[tuple[list[str], Any]],
) -> None:
    """Apply updates to a JSONC file in place."""
    path = Path(fpath)
    text = path.read_text()
    updated_text = update_jsonc_text(text, updates)
    path.write_text(updated_text)
