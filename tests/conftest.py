from __future__ import annotations

import json
from pathlib import Path


def global_config_file() -> Path:
    return Path(__file__).parent / "data" / "test_global_configs.json"


def global_config_for_testing(pth: Path) -> dict:
    """Set up configuration for testing and create required directories."""
    with open(global_config_file(), "r") as f:
        global_configs = json.load(f)

    global_configs["DATASET_ROOT"] = str(pth)

    (pth / "bids").mkdir(parents=True, exist_ok=True)

    return global_configs
