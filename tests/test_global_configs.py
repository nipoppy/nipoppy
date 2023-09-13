import json
from tempfile import NamedTemporaryFile

import pytest

from .conftest import global_config_file
from nipoppy.base import GlobalConfigs

def test_global_config_not_found():
    with pytest.raises(FileNotFoundError):
        GlobalConfigs('fake_path.json')

@pytest.mark.parametrize(
    'required_field',
    [
        'DATASET_NAME',
        'DATASET_ROOT',
        'CONTAINER_STORE',
        'SINGULARITY_PATH',
        'SESSIONS',
        'VISITS',
        'BIDS',
        'PROC_PIPELINES',
        'TABULAR',
        'WORKFLOWS',
    ],
)
def test_global_config_missing_required_field(required_field):

    with global_config_file().open('r') as file_global_configs:
        global_configs: dict = json.load(file_global_configs)
    invalid_global_configs = global_configs.copy()
    invalid_global_configs.pop(required_field)

    with NamedTemporaryFile('w') as file_invalid_global_configs:
        json.dump(invalid_global_configs, file_invalid_global_configs)
        file_invalid_global_configs.flush()
        with pytest.raises(KeyError, match='Missing required field in global config'):
            GlobalConfigs(file_invalid_global_configs.name)
