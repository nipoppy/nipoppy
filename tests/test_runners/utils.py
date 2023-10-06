import pytest
from pathlib import Path

from nipoppy.base import GlobalConfigs

def fpath_global_configs() -> Path:
    return Path(__file__).parent.parent / "data" / "test_global_configs.json"

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
