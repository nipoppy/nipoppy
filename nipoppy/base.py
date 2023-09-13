import json
from pathlib import Path

class GlobalConfigs():

    def __init__(self, fpath_global_configs) -> None:
        """Load global configs from file."""

        fpath_global_configs = Path(fpath_global_configs)
        if not fpath_global_configs.exists():
            raise FileNotFoundError(
                f'Global configs file does not exist: {fpath_global_configs}'
            )
        
        with open(fpath_global_configs, 'r') as file_global_configs:
            self._global_configs = json.load(file_global_configs)

        # TODO use a schema for validation
        try:
            self.dataset_name = Path(self._global_configs['DATASET_NAME'])
            self.dataset_root = Path(self._global_configs['DATASET_ROOT'])
            self.container_store: str = self._global_configs['CONTAINER_STORE']
            self.singularity_path: str = self._global_configs['SINGULARITY_PATH']
            self.sessions: list[str] = self._global_configs['SESSIONS']
            self.visits: list[str] = self._global_configs['VISITS']
            self.bids: dict[str, dict] = self._global_configs['BIDS']
            self.pipelines: dict[str, dict] = self._global_configs['PROC_PIPELINES']
            self.tabular: dict[str, dict] = self._global_configs['TABULAR']
            self.workflows: list = self._global_configs['WORKFLOWS']
        except KeyError as exception:
            raise KeyError(
                f'Missing required field in global configs: {exception}'
            )

    @property
    def fpath_manifest(self) -> Path:
        """Path to manifest file."""
        return # TODO
    
    @property
    def fpath_doughnut(self) -> Path:
        """Path to doughnut file."""
        return # TODO
    
    @property
    def fpath_derivatives_bagel(self) -> Path:
        """Path to derivatives bagel file."""
        return # TODO

