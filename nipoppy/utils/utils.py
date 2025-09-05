"""Utility functions."""

from __future__ import annotations

import datetime
import json
import os
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from nipoppy.env import (
    NIPOPPY_DIR_NAME,
    StrOrPathLike,
)

if TYPE_CHECKING:
    import pandas as pd


# user configs (pipeline configs, invocations, descriptors)
TEMPLATE_REPLACE_PATTERN = re.compile("\\[\\[NIPOPPY\\_(.*?)\\]\\]")

# paths
NIPOPPY_ROOT = Path(__file__).parents[1]
DPATH_DATA = NIPOPPY_ROOT / "data"
DPATH_EXAMPLES = DPATH_DATA / "examples"
FPATH_SAMPLE_CONFIG = DPATH_EXAMPLES / "sample_global_config.json"
FPATH_SAMPLE_MANIFEST = DPATH_EXAMPLES / "sample_manifest.tsv"
FPATH_SAMPLE_DICOM_DIR_MAP = DPATH_EXAMPLES / "sample_dicom_dir_map.tsv"
DPATH_LAYOUTS = DPATH_DATA / "layouts"
FPATH_DEFAULT_LAYOUT = DPATH_LAYOUTS / "layout-default.json"
DPATH_HPC = DPATH_DATA / "hpc"
FPATH_HPC_TEMPLATE = DPATH_HPC / "job_script_template.sh"
TEMPLATE_PIPELINE_PATH = NIPOPPY_ROOT / "data" / "template_pipeline"

# descriptions for common fields in the Pydantic models
FIELD_DESCRIPTION_MAP = {
    "participant_id": "Participant identifier, without the BIDS prefix",
    "session_id": "Imaging session identifier, without the BIDS prefix",
    "bids_participant_id": "Participant identifier with BIDS prefix (e.g., sub-01)",
    "bids_session_id": "Imaging session identifier with BIDS prefix (e.g., ses-01)",
    "visit_id": "Visit identifier",
}


def get_pipeline_tag(
    pipeline_name: str,
    pipeline_version: str,
    pipeline_step: Optional[str] = None,
    participant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    sep="-",
):
    """Generate a tag for a pipeline."""
    components = [pipeline_name, pipeline_version]
    if pipeline_step is not None:
        components.append(pipeline_step)
    if participant_id is not None:
        components.append(participant_id)
    if session_id is not None:
        components.append(session_id)
    return sep.join(components)


def load_json(fpath: StrOrPathLike, **kwargs) -> dict:
    """Load a JSON file.

    Parameters
    ----------
    fpath : nipoppy.env.StrOrPathLike
        Path to the JSON file
    **kwargs :
        Keyword arguments to pass to json.load

    Returns
    -------
    dict
        The JSON object.
    """
    with open(fpath, "r") as file:
        try:
            return json.load(file, **kwargs)
        except json.JSONDecodeError as exception:
            raise json.JSONDecodeError(
                f"Error loading JSON file at {fpath}", exception.doc, exception.pos
            )


def save_json(obj: dict, fpath: StrOrPathLike, **kwargs):
    """Save a JSON object to a file.

    Parameters
    ----------
    obj : dict
        The JSON object
    fpath : nipoppy.env.StrOrPathLike
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


def add_path_suffix(path: StrOrPathLike, suffix: str, sep="-") -> Path:
    """Add a suffix to a path, before the last file extension (if any)."""
    path = Path(path)
    return Path(path.parent, f"{path.stem}{sep}{suffix}{path.suffix}")


def add_path_timestamp(
    path: StrOrPathLike, timestamp_format="%Y%m%d_%H%M", sep="-"
) -> Path:
    """Add a timestamp to a path, before the last file extension (if any)."""
    timestamp = datetime.datetime.now().strftime(timestamp_format)
    return add_path_suffix(path=path, suffix=timestamp, sep=sep)


def save_df_with_backup(
    df: pd.DataFrame,
    fpath_symlink: StrOrPathLike,
    dname_backups: Optional[str] = None,
    use_relative_path=True,
    dry_run=False,
    **kwargs,
) -> Path | None:
    """Save a dataframe as a symlink pointing to a timestamped "backup" file.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to save
    fpath_symlink : nipoppy.env.StrOrPathLike
        The path to the symlink
    dname_backups : Optional[str], optional
        The directory where the timestamped backup file should be written
        (automatically determined if None), by default None
    use_relative_path : bool, optional
        Use relative instead of absolute path for the symlink, by default True
    dry_run : bool, optional
        Return the file path but do not save the file, by default False

    Returns
    -------
    Path or None
        None if no file was saved, otherwise the path to the backup file
    """
    if "index" not in kwargs:
        kwargs["index"] = False
    if "sep" not in kwargs:
        kwargs["sep"] = "\t"

    fpath_symlink: Path = Path(fpath_symlink)

    fname_backup = add_path_timestamp(fpath_symlink.name)
    if dname_backups is None:
        file_stem = fpath_symlink.stem
        # make it plural
        if file_stem.endswith("status"):
            suffix = "es"
        else:
            suffix = "s"
        dname_backups = f".{fpath_symlink.stem}{suffix}"

    fpath_backup_full: Path = fpath_symlink.parent / dname_backups / fname_backup

    if not dry_run:
        fpath_backup_full.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(fpath_backup_full, **kwargs)

        if use_relative_path:
            fpath_backup_to_link = os.path.relpath(
                fpath_backup_full, fpath_symlink.parent
            )
        else:
            fpath_backup_to_link = fpath_backup_full

        if fpath_symlink.is_symlink() or fpath_symlink.exists():
            fpath_symlink.unlink()
        fpath_symlink.symlink_to(fpath_backup_to_link)

    return Path(fpath_backup_full)


def process_template_str(
    template_str: str,
    resolve_paths=True,
    objs=None,
    **kwargs,
) -> str:
    """Replace template strings with values from kwargs or objects."""

    def replace(json_str: str, to_replace: str, replacement):
        if replacement is None:
            warnings.warn(f"Replacing {to_replace} with None")
        if resolve_paths and isinstance(replacement, Path):
            replacement = replacement.resolve()
        return json_str.replace(to_replace, str(replacement))

    def replace_from_objs(json_str: str, to_replace: str, objs):
        for obj in objs:
            if hasattr(obj, replacement_key):
                return replace(json_str, to_replace, getattr(obj, replacement_key))
        warnings.warn(f"Unable to replace {to_replace} in {template_str_original}")
        return json_str

    if objs is None:
        objs = []

    template_str_original = template_str

    matches = TEMPLATE_REPLACE_PATTERN.finditer(template_str)
    for match in matches:
        if len(match.groups()) != 1:
            raise ValueError(f"Expected exactly one match group for match: {match}")
        to_replace = match.group()
        replacement_key = match.groups()[0].lower()  # always convert to lowercase

        if not str.isidentifier(replacement_key):
            raise ValueError(
                f"Invalid identifier name {replacement_key} in {template_str}"
            )

        if replacement_key in kwargs:
            template_str = replace(template_str, to_replace, kwargs[replacement_key])
        else:
            template_str = replace_from_objs(template_str, to_replace, objs)

    return template_str


def apply_substitutions_to_json(
    json_obj: dict | list, substitutions: dict[str, str]
) -> dict | list:
    """Apply substitutions to a JSON object."""
    # convert json_obj to string
    json_text = json.dumps(json_obj)
    for key, value in substitutions.items():
        json_text = json_text.replace(key, value)
    return json.loads(json_text)


def get_today():
    """Get today's date in the format YYYY-MM-DD."""
    return datetime.datetime.today().strftime("%Y-%m-%d")


def is_nipoppy_project(cwd=Path.cwd()):
    """Verify if the current directory is a nipoppy project.

    This is done by checking if the `.nipoppy` directory exists in the
    current directory or any of its parents.
    If the directory is found, it returns the path to the `.nipoppy`
    directory. If not, it returns False.

    Parameters
    ----------
    cwd : nipoppy.env.StrOrPathLike, optional
        Path to directory, by default Path.cwd()
    """
    current = Path(cwd).resolve()
    while True:
        candidate = current / NIPOPPY_DIR_NAME
        if candidate.is_dir():
            return current  # Found
        if current == Path("/"):
            return False  # Reached root, not found
        current = current.parent
