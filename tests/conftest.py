from __future__ import annotations

import json
import shutil
from pathlib import Path


def _global_config_file() -> Path:
    return Path(__file__).parent / "data" / "test_global_configs.json"


def _global_config_for_testing(pth: Path) -> dict:
    """Set up configuration for testing and create required directories."""
    with open(_global_config_file(), "r") as f:
        global_configs = json.load(f)

    global_configs["DATASET_ROOT"] = str(pth)

    (pth / "bids").mkdir(parents=True, exist_ok=True)

    return global_configs


def _dummy_bids_filter_file(pth: Path) -> Path:
    """TODO probably don't want the bids filter file to be in the module directory"""
    return pth / "bids_filter.json"


def _create_dummy_bids_filter(pth: Path) -> None:
    with open(_dummy_bids_filter_file(pth), "w") as f:
        json.dump({"dummy": "dummy"}, f)


def _delete_dummy_bids_filter(pth: Path) -> None:
    _dummy_bids_filter_file(pth).unlink(missing_ok=True)


def _mock_bids_dataset(pth: Path, dataset: str) -> Path:
    """Copy a BIDS example dataset to the given path."""
    ds = Path(__file__).parent / "data" / dataset
    print(f"\nCopying {ds} to {pth}\n")
    shutil.copytree(
        ds,
        pth,
        symlinks=True,
        ignore_dangling_symlinks=True,
        dirs_exist_ok=True,
    )

    return pth / "bids"
