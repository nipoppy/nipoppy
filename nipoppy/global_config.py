import json
from pathlib import Path

class GlobalConfig():

    # TODO use schema
    required_fields = [
        "DATASET_ROOT",
        "CONTAINER_STORE",
        "SINGULARITY_PATH",
        "SESSIONS",
        "VISITS",
        "BIDS",
        "PROC_PIPELINES",
        "TABULAR",
    ]

    def __init__(self, fpath_global_config) -> None:

        fpath_global_config = Path(fpath_global_config)
        if not fpath_global_config.exists():
            raise FileNotFoundError(f'Global config file not found: {fpath_global_config}')
        
        with open(fpath_global_config, 'r') as file_global_config:
            self._global_config = json.load(file_global_config)

    def validate(self):
        pass
