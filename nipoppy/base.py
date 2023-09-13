from __future__ import annotations
import json
from pathlib import Path
from typing import Mapping

class GlobalConfigs():

    # TODO load tree.json as an object?

    class Program():

        def __init__(self, name, program_dict) -> None:
            self.name = name
            self._program_dict = program_dict
            try:
                # required field(s)
                self.version = program_dict['VERSION']
            except KeyError as exception:
                self.raise_missing_field_error(exception)

        @property
        def container(self) -> str:
            return self._get_optional_field('CONTAINER')

        @property
        def invocation_template(self) -> str:
            return self._get_optional_field('INVOCATION_TEMPLATE')

        def _get_optional_field(self, field_name):
            try:
                return self._program_dict[field_name]
            except KeyError as exception:
                self.raise_missing_field_error(exception)
            
        def raise_missing_field_error(self, original_exception):
            GlobalConfigs.raise_missing_field_error(
                original_exception,
                message_suffix=f'for program: {self.name}',
            )

    def __init__(self, fpath_global_configs) -> None:
        """Load global configs from file."""

        fpath_global_configs = Path(fpath_global_configs)
        if not fpath_global_configs.exists():
            raise FileNotFoundError(
                f'Global configs file does not exist: {fpath_global_configs}'
            )
        
        with open(fpath_global_configs, 'r') as file_global_configs:
            self._global_configs_dict = json.load(file_global_configs)

        # TODO use a schema for validation ?
        try:
            self.dataset_name = Path(self._global_configs_dict['DATASET_NAME'])
            self.dataset_root = Path(self._global_configs_dict['DATASET_ROOT'])
            self.container_store: str = self._global_configs_dict['CONTAINER_STORE']
            self.singularity_path: str = self._global_configs_dict['SINGULARITY_PATH']
            self.sessions: list[str] = self._global_configs_dict['SESSIONS']
            self.visits: list[str] = self._global_configs_dict['VISITS']
            self.bids = self._load_and_validate_programs(
                self._global_configs_dict['BIDS']
            )
            self.pipelines = self._load_and_validate_programs(
                self._global_configs_dict['PROC_PIPELINES']
            )
            self.tabular: dict[str, dict] = self._global_configs_dict['TABULAR']
            self.workflows: list = self._global_configs_dict['WORKFLOWS']
        except KeyError as exception:
            self.raise_missing_field_error(exception)

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
    
    def _load_and_validate_programs(self, program_names_and_dicts: Mapping[str, Mapping]) -> dict[str, Program]:
        return {
            name: self.Program(name, program_dict)
            for name, program_dict in
            program_names_and_dicts.items()
        }
    
    @classmethod
    def _get_program(cls, program_names_and_dicts: Mapping[str, GlobalConfigs.Program], program_name: str) -> GlobalConfigs.Program:
        try:
            program = program_names_and_dicts[program_name]
        except KeyError:
            raise RuntimeError(
                f'Program \'{program_name}\' not found in global configs'
            )
        return program

    @classmethod
    def _check_program_version(cls, program_names_and_dicts: Mapping[str, GlobalConfigs.Program], program_name: str, program_version: str | None = None) -> str:
        program = cls._get_program(program_names_and_dicts, program_name)
        
        if program_version is None:
            program_version = program.version
        elif program_version != program.version:
            raise RuntimeError(
                f'Version mismatch for program \'{program_name}\':'
                f' {program_version} != {program.version}'
            )
        return program_version

    def check_pipeline_version(self, pipeline_name: str, pipeline_version: str | None = None) -> str:
        return self._check_program_version(
            self.pipelines,
            pipeline_name,
            pipeline_version,
        )
    
    def _get_container(self, program_names_and_dicts: Mapping[str, GlobalConfigs.Program], program_name, program_version=None):
        program = self._get_program(program_names_and_dicts, program_name)
        program_version = self._check_program_version(program_names_and_dicts, program_name, program_version)
        return Path(self.container_store) / program.container.format(program_version)
    
    def get_pipeline_container(self, pipeline_name: str, pipeline_version: str | None = None) -> Path:
        return self._get_container(self.pipelines, pipeline_name, pipeline_version)

    @staticmethod
    def _get_invocation_template(program_dict: Mapping[str, GlobalConfigs.Program], program_name: str, program_version: str):
        for program in program_dict.values():
            if program.name == program_name and program.version == program_version:
                invocation_template = Path(program.invocation_template) # TODO add logic for relative paths?
                if not invocation_template.exists():
                    raise FileNotFoundError(
                        'Invocation template file does not exist for program'
                        f' {program_name}, version {program_version}'
                        f': {invocation_template}')
                return invocation_template
        raise RuntimeError(
            'No invocation template found'
            f' for program \'{program_name}\', version \'{program_version}\''
        )
        
    def get_bids_invocation_template(self, name: str, version: str) -> Path:
        return self._get_invocation_template(self.bids, name, version)

    def get_pipeline_invocation_template(self, name: str, version: str) -> Path:
        return self._get_invocation_template(self.pipelines, name, version)
    
    class MissingFieldException(Exception):
        def __init__(self, field, message_suffix='') -> None:
            if not message_suffix.startswith(' '):
                message_suffix = f' {message_suffix}'
            self.field = field
            self.message_suffix = message_suffix
            self.message = f'Missing field {field}{message_suffix}'
            super().__init__(self.message)

    @staticmethod
    def raise_missing_field_error(original_exception, message_suffix='from global configs'):
        raise GlobalConfigs.MissingFieldException(original_exception, message_suffix=message_suffix)
