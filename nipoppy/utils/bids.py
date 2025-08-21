"""Utility functions for BIDS dataset manipulation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Sequence

import bids

from nipoppy.env import BIDS_SESSION_PREFIX, BIDS_SUBJECT_PREFIX, StrOrPathLike


def participant_id_to_bids_participant_id(participant_id: str) -> str:
    """Add the BIDS prefix to a participant ID."""
    return f"{BIDS_SUBJECT_PREFIX}{participant_id}"


def session_id_to_bids_session_id(session_id: Optional[str]) -> str:
    """
    Add the BIDS prefix to a session ID.

    If session_id is None, returns None.
    """
    if session_id is None:
        return session_id

    return f"{BIDS_SESSION_PREFIX}{session_id}"


def check_participant_id(participant_id: Optional[str], raise_error=False):
    """Make sure a participant ID is valid.

    Specifically:
    - Check that it does not have the `sub-` prefix, stripping it if it does
    - Check that it only has alphanumeric characters

    Parameters
    ----------
    participant_id : Optional[str]
        The participant ID to check. If None, returns None.
    raise_error : bool, optional
        Whether to raise an error if the participant ID has the `sub-` prefix, by
        default False. Note: an error is always raised if the participant ID contains
        non-alphanumeric characters after being stripped of the `sub-` prefix.

    Returns
    -------
    str
        The participant ID without the BIDS prefix

    Raises
    ------
    ValueError
    """
    if participant_id is None:
        return participant_id

    if participant_id.startswith(BIDS_SUBJECT_PREFIX):
        if raise_error:
            raise ValueError(
                f'Invalid participant ID: should not start with "{BIDS_SUBJECT_PREFIX}"'
                f", got {participant_id}"
            )
        else:
            participant_id = participant_id.removeprefix(BIDS_SUBJECT_PREFIX)

    if not participant_id.isalnum():
        raise ValueError(
            f"Invalid participant ID: must only contain alphanumeric characters, "
            f"got {participant_id}"
        )

    return participant_id


def check_session_id(session_id: Optional[str], raise_error=False):
    """Make sure a session ID is valid.

    Specifically:
    - Check that it does not have the `ses-` prefix, stripping it if it does
    - Check that it only has alphanumeric characters

    Parameters
    ----------
    participant_id : Optional[str]
        The participant ID to check. If None, returns None.
    raise_error : bool, optional
        Whether to raise an error if the session ID has the `ses-` prefix, by default
        False. Note: an error is always raised if the session ID contains
        non-alphanumeric characters even being stripped of the `ses-` prefix.

    Returns
    -------
    str
        The session ID without the BIDS prefix

    Raises
    ------
    ValueError
    """
    if session_id is None:
        return session_id

    if session_id.startswith(BIDS_SESSION_PREFIX):
        if raise_error:
            raise ValueError(
                f'Invalid session ID: should not start with "{BIDS_SESSION_PREFIX}"'
                f", got {session_id}"
            )
        else:
            session_id = session_id.removeprefix(BIDS_SESSION_PREFIX)

    if not session_id.isalnum():
        raise ValueError(
            f"Invalid session ID: must only contain alphanumeric characters, "
            f"got {session_id}"
        )

    return session_id


def create_bids_db(
    dpath_bids: StrOrPathLike,
    dpath_pybids_db: Optional[StrOrPathLike] = None,
    validate=False,
    reset_database=True,
    ignore_patterns: Optional[list[str | re.Pattern] | str | re.Pattern] = None,
    resolve_paths=True,
) -> bids.BIDSLayout:
    """Create a BIDSLayout using an indexer."""
    dpath_bids = Path(dpath_bids)
    if resolve_paths:
        dpath_bids = dpath_bids.resolve()

    if dpath_pybids_db is not None:
        dpath_pybids_db = Path(dpath_pybids_db)

    indexer = bids.BIDSLayoutIndexer(
        validate=validate,
        ignore=ignore_patterns,
    )
    bids_layout = bids.BIDSLayout(
        root=dpath_bids,
        indexer=indexer,
        validate=validate,
        database_path=dpath_pybids_db,
        reset_database=reset_database,
    )
    return bids_layout


def add_pybids_ignore_patterns(
    current: List[re.Pattern],
    new: Sequence[str | re.Pattern] | str | re.Pattern,
):
    """Add pattern(s) to ignore for PyBIDS."""
    if isinstance(new, (str, re.Pattern)):
        new = [new]
    for pattern in new:
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        if pattern not in current:
            current.append(pattern)
