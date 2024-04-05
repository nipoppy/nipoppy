"""Utility functions."""

import datetime
import json
import os
import re
from pathlib import Path
from typing import Optional

import bids
import pandas as pd

# BIDS
BIDS_SUBJECT_PREFIX = "sub-"
BIDS_SESSION_PREFIX = "ses-"

# user configs (pipeline configs, invocations, descriptors)
TEMPLATE_REPLACE_PATTERN = re.compile("\\[\\[NIPOPPY\\_(.*?)\\]\\]")

# paths
DPATH_DATA = Path(__file__).parent / "data"
DPATH_SAMPLE_DATA = DPATH_DATA / "sample_data"
FPATH_SAMPLE_CONFIG = DPATH_SAMPLE_DATA / "sample_global_configs.json"
FPATH_SAMPLE_MANIFEST = DPATH_SAMPLE_DATA / "sample_manifest.csv"
DPATH_DESCRIPTORS = DPATH_DATA / "descriptors"
DPATH_LAYOUT = DPATH_DATA / "layout"
FPATH_DEFAULT_LAYOUT = DPATH_LAYOUT / "layout-default.json"


def participant_id_to_dicom_id(participant_id: str):
    """Convert a participant ID to a BIDS-compatible DICOM ID."""
    # keep only alphanumeric characters
    participant_id = str(participant_id)
    dicom_id = "".join(filter(str.isalnum, participant_id))
    return dicom_id


def dicom_id_to_bids_id(dicom_id: str):
    """Add the BIDS prefix to a DICOM ID."""
    return f"{BIDS_SUBJECT_PREFIX}{dicom_id}"


def participant_id_to_bids_id(participant_id: str):
    """Convert a participant ID to a BIDS-compatible participant ID."""
    bids_id = dicom_id_to_bids_id(participant_id_to_dicom_id(participant_id))
    return bids_id


def check_participant(participant: Optional[str]):
    """Check/process a participant string."""
    if participant is None:
        return participant

    # remove the BIDS prefix if it exists
    return str(participant).removeprefix(BIDS_SUBJECT_PREFIX)


def check_session(session: Optional[str]):
    """Check/process a session string."""
    if session is None:
        return session

    # add BIDS prefix if it doesn't already exist
    session = str(session)
    if session.startswith(BIDS_SESSION_PREFIX):
        return session
    else:
        return f"{BIDS_SESSION_PREFIX}{session}"


def strip_session(session: Optional[str]):
    """Strip the BIDS prefix from a session string."""
    if session is None:
        return session
    session = str(session)
    return session.removeprefix(BIDS_SESSION_PREFIX)


def create_bids_db(
    dpath_bids: Path | str,
    dpath_bids_db: Optional[Path | str] = None,
    validate=False,
    reset_database=True,
    ignore_patterns: Optional[list[str | re.Pattern] | str | re.Pattern] = None,
    resolve_paths=True,
) -> bids.BIDSLayout:
    """Create a BIDSLayout using an indexer."""
    dpath_bids = Path(dpath_bids)
    if resolve_paths:
        dpath_bids = dpath_bids.resolve()

    if dpath_bids_db is not None:
        dpath_bids_db = Path(dpath_bids_db)

    indexer = bids.BIDSLayoutIndexer(
        validate=validate,
        ignore=ignore_patterns,
    )
    bids_layout = bids.BIDSLayout(
        root=dpath_bids,
        indexer=indexer,
        validate=validate,
        database_path=dpath_bids_db,
        reset_database=reset_database,
    )
    return bids_layout


def get_pipeline_tag(
    pipeline_name: str,
    pipeline_version: str,
    pipeline_step: Optional[str] = None,
    participant: Optional[str] = None,
    session: Optional[str] = None,
    sep="-",
):
    """Generate a tag for a pipeline."""
    components = [pipeline_name, pipeline_version]
    if pipeline_step is not None:
        components.append(pipeline_step)
    if participant is not None:
        components.append(participant)
    if session is not None:
        components.append(strip_session(session))
    return sep.join(components)


def load_json(fpath: str | Path, **kwargs) -> dict:
    """Load a JSON file.

    Parameters
    ----------
    fpath : str | Path
        Path to the JSON file
    **kwargs :
        Keyword arguments to pass to json.load

    Returns
    -------
    dict
        The JSON object.
    """
    with open(fpath, "r") as file:
        return json.load(file, **kwargs)


def save_json(obj: dict, fpath: str | Path, **kwargs):
    """Save a JSON object to a file.

    Parameters
    ----------
    obj : dict
        The JSON object
    fpath : str | Path
        Path to the JSON file to write
    indent : int, optional
        Indentation level, by default 4
    **kwargs :
        Keyword arguments to pass to json.dump
    """
    if "indent" not in kwargs:
        kwargs["indent"] = 4
    fpath = Path(fpath)
    fpath.parent.mkdir(parents=True, exist_ok=True)
    with open(fpath, "w") as file:
        json.dump(obj, file, **kwargs)


def save_df_with_backup(
    df: pd.DataFrame,
    fpath_symlink: str | Path,
    dname_backups: Optional[str] = None,
    use_relative_path=True,
    timestamp_format="%Y%m%d_%H%M",
    ext_symbol=".",
    sep_fname_backup="-",
    **kwargs,
):
    """Save a dataframe as a symlink pointing to a timestamped "backup" file.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to save
    fpath_symlink : str | Path
        The path to the symlink
    dname_backups : Optional[str], optional
        The directory where the timestamped backup file should be written
        (automatically determined if None), by default None
    use_relative_path : bool, optional
        Use relative instead of absolute path for the symlink, by default True
    timestamp_format : str, optional
        Format string for strftime, by default "%Y%m%d_%H%M"
    ext_symbol : str, optional
        File extension separator, by default "."
    sep_fname_backup : str, optional
        Separator before the timestamp in name of the backup file, by default "-"

    Returns
    -------
    Path
        _description_
    """
    if "index" not in kwargs:
        kwargs["index"] = False

    fpath_symlink = Path(fpath_symlink)

    timestamp_format = datetime.datetime.now().strftime(timestamp_format)
    fpath_symlink_components = fpath_symlink.name.split(ext_symbol)
    fname_backup = ext_symbol.join(
        [f"{fpath_symlink_components[0]}{sep_fname_backup}{timestamp_format}"]
        + fpath_symlink_components[1:]
    )
    if dname_backups is None:
        dname_backups = f".{fpath_symlink_components[0]}s"

    fpath_backup_full: Path = fpath_symlink.parent / dname_backups / fname_backup

    fpath_backup_full.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fpath_backup_full, **kwargs)
    os.chmod(fpath_backup_full, 0o664)

    if use_relative_path:
        fpath_backup_to_link = os.path.relpath(fpath_backup_full, fpath_symlink.parent)
    else:
        fpath_backup_to_link = fpath_backup_full

    if fpath_symlink.exists():
        fpath_symlink.unlink()
    fpath_symlink.symlink_to(fpath_backup_to_link)

    return Path(fpath_backup_full)


def process_template_str(
    template_str: str, resolve_paths=True, objs=None, lower=True, **kwargs
) -> str:
    """Replace template strings with values from kwargs or objects."""

    def replace(json_str: str, to_replace: str, replacement):
        if resolve_paths and isinstance(replacement, Path):
            replacement = replacement.resolve()
        return json_str.replace(to_replace, str(replacement))

    def replace_from_objs(json_str: str, to_replace: str, objs):
        for obj in objs:
            if hasattr(obj, replacement_key):
                return replace(json_str, to_replace, getattr(obj, replacement_key))
        raise RuntimeError(f"Unable to replace {to_replace} in {template_str_original}")

    if objs is None:
        objs = []

    template_str_original = template_str

    matches = TEMPLATE_REPLACE_PATTERN.finditer(template_str)
    for match in matches:
        if len(match.groups()) != 1:
            raise ValueError(f"Expected exactly one match group for match: {match}")
        to_replace = match.group()
        replacement_key = match.groups()[0]
        if lower:
            replacement_key = replacement_key.lower()

        if not str.isidentifier(replacement_key):
            raise ValueError(
                f"Invalid identifier name {replacement_key} in {template_str}"
            )

        if replacement_key in kwargs:
            template_str = replace(template_str, to_replace, kwargs[replacement_key])
        else:
            template_str = replace_from_objs(template_str, to_replace, objs)

    return template_str