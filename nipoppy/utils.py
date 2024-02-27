"""Utility functions."""

import datetime
import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

# BIDS
BIDS_SUBJECT_PREFIX = "sub-"
BIDS_SESSION_PREFIX = "ses-"

# paths
FPATH_DATA = Path(__file__).parent / "data"
FPATH_SAMPLE_CONFIG = FPATH_DATA / "sample_global_configs.json"
FPATH_SAMPLE_MANIFEST = FPATH_DATA / "sample_manifest.csv"


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
    # TODO allow custom_map (?)
    # if custom_map == None:
    #     bids_id = dicom_id_to_bids_id(participant_id_to_dicom_id(participant_id))
    # else:
    #     _df = pd.read_csv(custom_map)
    #     bids_id =_df.loc[(_df["participant_id"]==participant_id)]["bids_id"].values[0]
    return bids_id


def check_session(session: str):
    """Check/process a session string."""
    # add BIDS prefix if it doesn't already exist
    session = str(session)
    if session.startswith(BIDS_SESSION_PREFIX):
        return session
    else:
        return f"{BIDS_SESSION_PREFIX}{session}"


def strip_session(session: str):
    """Strip the BIDS prefix from a session string."""
    session = str(session)
    return session.removeprefix(BIDS_SESSION_PREFIX)


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
