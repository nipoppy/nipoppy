from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Iterable, Mapping

class GlobalConfigs():

    # TODO load tree.json as an object?

    class Program():

        name = None

        def __init__(self, name, config) -> None:
            self.name = name
            self._config = config
            try:
                # required field(s)
                self.version = self._process_version(config['VERSION'])
                self.fname_container_template: str = config['CONTAINER']
            except KeyError as exception:
                self.raise_missing_field_error(exception)

        def _get_optional_field(self, field_name):
            try:
                return self._config[field_name]
            except KeyError as exception:
                self.raise_missing_field_error(exception)

        @property
        def invocation_template(self) -> str:
            return self._get_optional_field('INVOCATION_TEMPLATE')

        def get_fname_container(self, version: str | None = None) -> str:
            return self.fname_container_template.format(self.check_version(version))
        
        def get_fpath_invocation_template(self, version: str | None = None) -> Path:
            fpath_invocation_template = Path(
                self.invocation_template.format(self.check_version(version))
            )
            return fpath_invocation_template

        def _process_version(self, version: str | Iterable[str]):
            if isinstance(version, str):
                version = [version]
            if len(version) == 0:
                if self.name is not None:
                    message_suffix = f' given for pipeline {self.name}'
                else:
                    message_suffix = ''
                raise ValueError(f'No version(s){message_suffix}')
            return version

        def check_version(self, version: str | None):
            if version is None:
                version = self.version[0]
            elif version not in self.version:
                raise RuntimeError(
                    f'Version mismatch for program {self.name}: '
                    f'{version} != {self.version}'
                )
            return version

        def raise_missing_field_error(self, original_exception):
            raise GlobalConfigs.MissingFieldException(
                original_exception,
                message_suffix=f'for program: {self.name}',
            )

    def __init__(self, fpath_or_dict) -> None:
        """Load global configs from file."""

        self.fpath_or_dict = fpath_or_dict
        self._global_configs_dict = self._get_json_dict(fpath_or_dict)

        # TODO use a schema for validation ?
        try:
            self.dataset_name = Path(self._global_configs_dict['DATASET_NAME'])
            self.dataset_root = Path(self._global_configs_dict['DATASET_ROOT'])
            self.container_store: str = self._global_configs_dict['CONTAINER_STORE']
            self.singularity_path: str = self._global_configs_dict['SINGULARITY_PATH']
            self.sessions: list[str] = self._global_configs_dict['SESSIONS']
            self.visits: list[str] = self._global_configs_dict['VISITS']
            self.tabular: dict[str, dict] = self._global_configs_dict['TABULAR']
            self.workflows: list = self._global_configs_dict['WORKFLOWS']
            # self.bids = self._process_programs(
            #     self._global_configs_dict['BIDS']
            # )
            # self.pipelines = self._process_programs(
            #     self._global_configs_dict['PROC_PIPELINES']
            # )
            self.programs = self._process_programs(
                self._global_configs_dict['BIDS'],
                self._global_configs_dict['PROC_PIPELINES'],
            )
        except KeyError as exception:
            self.raise_missing_field_error(exception)

        # TODO define fpath_{manifest/doughnut/derivatives_bagel} here?

    # @property
    # def fpath_manifest(self) -> Path:
    #     """Path to manifest file."""
    #     return # TODO
    
    # @property
    # def fpath_doughnut(self) -> Path:
    #     """Path to doughnut file."""
    #     return # TODO
    
    # @property
    # def fpath_derivatives_bagel(self) -> Path:
        """Path to derivatives bagel file."""
        return # TODO
    
    @classmethod
    def _get_json_dict(cls, fpath_or_dict) -> dict:
        
        if isinstance(fpath_or_dict, dict):
            return fpath_or_dict
        
        elif isinstance(fpath_or_dict, (str, os.PathLike)):
            fpath_global_configs = Path(fpath_or_dict)
            if not fpath_global_configs.exists():
                raise FileNotFoundError(
                    f'Global configs file does not exist: {fpath_global_configs}'
                )
            
            with open(fpath_global_configs, 'r') as file_global_configs:
                return json.load(file_global_configs)
            
        else:
            raise TypeError(
                f'Expected a dict or a str/path-like object, '
                f'got {type(fpath_or_dict)}'
            )

    @classmethod
    def _process_programs(cls, *program_configs_all: Mapping[str, Mapping]) -> dict[str, Program]:
        programs = {}
        for program_configs in program_configs_all:
            for name, config in program_configs.items():
                if name in programs:
                    raise RuntimeError(
                        f'Program {name} is not unique'
                    )
                programs[name] = cls.Program(name, config)
        return programs
    
    def get_program(self, program_name: str) -> GlobalConfigs.Program:
        try:
            program = self.programs[program_name]
        except KeyError as exception:
            raise RuntimeError(
                f'Program {exception} not found in global configs. '
                f'Available programs are: {self.programs.keys()}'
            )
        return program

    def check_version(self, program_name: str, program_version: str | None = None) -> str:
        return self.get_program(program_name).check_version(program_version)

    def get_fpath_container(self, program_name: str, program_version: str | None = None) -> Path:
        program = self.get_program(program_name)
        return Path(self.container_store) / program.get_fname_container(program_version)

    def get_fpath_invocation_template(self, program_name: str, program_version: str | None = None) -> Path:
        program = self.get_program(program_name)
        return program.get_fpath_invocation_template(program_version)
    
    class MissingFieldException(Exception):
        def __init__(self, field, message_suffix='') -> None:
            if not message_suffix.startswith(' '):
                message_suffix = f' {message_suffix}'
            self.field = field
            self.message_suffix = message_suffix
            self.message = f'Missing field {field}{message_suffix}'
            super().__init__(self.message)

    def raise_missing_field_error(self, original_exception, message_suffix='from global configs'):
        raise self.MissingFieldException(original_exception, message_suffix=message_suffix)
