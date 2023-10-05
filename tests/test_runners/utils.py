import pytest
from pathlib import Path

from nipoppy.base import GlobalConfigs

def fpath_global_configs() -> Path:
    return Path(__file__).parent.parent / "data" / "test_global_configs.json"

@pytest.fixture
def global_configs_fixture() -> GlobalConfigs:
    return GlobalConfigs(fpath_global_configs())
