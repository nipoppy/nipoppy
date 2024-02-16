"""Utility functions."""

import json
from pathlib import Path

FPATH_DATA = Path(__file__).parent / "data"
FPATH_SAMPLE_CONFIG = FPATH_DATA / "sample_global_configs.json"
FPATH_SAMPLE_MANIFEST = FPATH_DATA / "sample_manifest.csv"


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
    with open(fpath, "w") as file:
        json.dump(obj, file, **kwargs)
