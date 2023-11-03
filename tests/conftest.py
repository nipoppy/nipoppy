from __future__ import annotations

import json
from pathlib import Path

import pytest
from nipoppy.base import GlobalConfigs

def global_configs_file() -> Path:
    return Path(__file__).parent / "data" / "test_global_configs.json"


def global_configs_for_testing(pth: Path) -> dict:
    """Set up configuration for testing and create required directories."""
    with open(global_configs_file(), "r") as f:
        global_configs = json.load(f)

    global_configs["DATASET_ROOT"] = str(pth)

    (pth / "bids").mkdir(parents=True, exist_ok=True)

    return global_configs


def fpath_global_configs() -> Path:
    return Path(__file__).parent / "data" / "test_global_configs.json"


@pytest.fixture(scope='package')
def global_configs_fixture() -> GlobalConfigs:
    return GlobalConfigs(fpath_global_configs())


@pytest.fixture(scope='package')
def dpath_tmp():
    return Path(__file__).parent / 'tmp'


@pytest.fixture(autouse=True)
def tmp_dir(dpath_tmp: Path):

    def remove_dir(dpath: Path):
        for subpath in dpath.iterdir():
            if subpath.is_dir():
                remove_dir(subpath)
            else:
                subpath.unlink()
        dpath.rmdir()

    dpath_tmp.mkdir(exist_ok=True)
    yield
    remove_dir(dpath_tmp)
