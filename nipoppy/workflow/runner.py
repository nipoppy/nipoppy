import json
import os
import subprocess
from abc import ABC, abstractmethod
from logging import Logger
from pathlib import Path
from typing import Sequence

import boutiques
from boutiques import bosh

from nipoppy.base import GlobalConfigs

class BaseRunner(ABC):
    
    # TODO add logger
    def __init__(self, global_configs, name=None, logging=True, dry_run=False) -> None:
        
        if isinstance(global_configs, (str, os.PathLike)):
            global_configs = GlobalConfigs(global_configs)

        self.global_configs = global_configs
        self.name = name
        self.logging = logging
        self.dry_run = dry_run

        self.logger = self.initialize_logger() # TODO
        self.command_history = []

    def run(self, *args, **kwargs):
        self.run_setup(*args, **kwargs)
        self.run_main(*args, **kwargs)
        self.run_cleanup(*args, **kwargs)

    def run_setup(self, *args, **kwargs):
        return

    @abstractmethod
    def run_main(self, *args, **kwargs):
        pass

    def run_cleanup(self, *args, **kwargs):
        return
    
    def initialize_logger(self) -> Logger:
        if self.logging:
            # TODO initialize logger with timestamp and self.name
            pass
        else:
            logger = None
        # return logger
    
    # TODO default logfile path
    def generate_fpath_log(self) -> Path:
        pass

    def run_commands(self, commands: Sequence[Sequence[str] | str]):
        for command in commands:
            self.run_command(command)

    def run_command(self, command: Sequence[str] | str):

        # build command string
        if not isinstance(command, str):
            command = self._args_to_command(command)

        self.log_command(command)

        if not self.dry_run:
            # TODO throw error on fail
            subprocess_result = subprocess.run(command.split())
            return subprocess_result
        
        self.command_history.append(command)
    
    def _args_to_command(self, args: Sequence[str]) -> str:
        return ' '.join([str(arg) for arg in args])

    def log_command(self, command: str):
        self.log(f'[NIPOPPY] {command}')
    
    def log(self, message, level=None):
        print(message)
        # if self.logging:
        #     # TODO log message
        #     pass
        # else:
        #     print(message)

    # TODO repr, str

class BaseParallelRunner(BaseRunner, ABC):

    def __init__(self, global_configs, n_jobs=1, *args, **kwargs) -> None:
        super().__init__(global_configs, *args, **kwargs)
        self.n_jobs = n_jobs

    def run_setup(self, *args, **kwargs):
        # TODO call get_args_for_parallel to get list of kwarg dicts
        # TODO validate list of kwarg dicts
        pass

    def run_main(self, *args, **kwargs):
        if self.n_jobs == 1:
            # TODO loop over args
            return self.to_run_in_parallel(*args, **kwargs)
        else:
            pass # TODO

    @abstractmethod
    def get_kwargs_for_parallel(self, *args, **kwargs):
        pass

    @abstractmethod
    def to_run_in_parallel(self, *args, **kwargs):
        pass

class BoutiquesRunner(BaseRunner):

    dpath_descriptors = Path(__file__).parent / 'descriptors'
    invocation_kwarg_replacement_map = {
        '[[NIPOPPY_SUBJECT]]': 'subject',
        '[[NIPOPPY_SESSION]]': 'session',
    }
    invocation_config_replacement_map = {
        '[[NIPOPPY_DATASET_ROOT]]': 'dataset_root',
        '[[NIPOPPY_DATASTORE_DIR]]': 'datastore_dir',
        '[[NIPOPPY_CONTAINER_STORE]]': 'container_store',
        '[[NIPOPPY_SINGULARITY_PATH]]': 'singularity_path',
    }

    def __init__(self, global_configs, pipeline_name: str, pipeline_version: str | None = None, *args, **kwargs) -> None:
        super().__init__(global_configs, *args, **kwargs)
        self.pipeline_name = pipeline_name
        self.pipeline_version = self.global_configs.check_pipeline_version(
            self.pipeline_name,
            pipeline_version,
        )

        self.descriptor = self.load_descriptor()
        self.invocation_template: str = self.load_invocation_template()

    def load_descriptor(self) -> str:
        fpath_descriptor_template = self.dpath_descriptors / f'{self.pipeline_name}-{self.pipeline_version}.json'
        with fpath_descriptor_template.open() as file:
            descriptor_template = json.load(file)
        descriptor_template = self.process_boutiques_json(json.dumps(descriptor_template))
        self.run_bosh_command(['validate', descriptor_template])
        return descriptor_template

    def load_invocation_template(self) -> str:
        fpath = self.global_configs.get_pipeline_invocation_template(
            self.pipeline_name,
            self.pipeline_version,
        )

        with fpath.open() as file:
            invocation_template = json.load(file)
        return json.dumps(invocation_template)
    
    def run(self, subject=None, session=None, *args, **kwargs):
        super().run(subject=subject, session=session, *args, **kwargs)

    def run_main(self, *args, **kwargs):

        invocation = self.process_boutiques_json(
            self.invocation_template,
            *args,
            **kwargs,
        )

        try:
            self.run_bosh_command(
                ['invocation', '-i', invocation, self.descriptor],
            )
        except boutiques.invocationSchemaHandler.InvocationValidationError:
            raise RuntimeError(
                f'Invalid invocation {invocation} '
                f'for descriptor at {self.descriptor}'
            )

        self.run_bosh_command(['exec', 'simulate', '-i', invocation, self.descriptor])
        self.run_bosh_command(['exec', 'launch', '--stream', self.descriptor, invocation])

    def process_boutiques_json(self, json_str: str, **kwargs) -> str:
        
        def replace(json_str: str, to_replace: str, replacement):
            return json_str.replace(to_replace, str(replacement))

        # replacements based on runtime arguments
        for to_replace, target_kwarg in self.invocation_kwarg_replacement_map.items():
            if to_replace in json_str:
                if target_kwarg not in kwargs or kwargs[target_kwarg] is None:
                    raise ValueError(
                        f'Expected keyword argument: {target_kwarg}. Cannot '
                        f'replace {to_replace} in invocation template')
                
                json_str = replace(
                    json_str,
                    to_replace,
                    kwargs[target_kwarg],
                )

        # replacement based on global configs
        for to_replace, target_attr in self.invocation_config_replacement_map.items():
            
            if to_replace in json_str:
                try:
                    replacement = getattr(self.global_configs, target_attr)
                except AttributeError:
                    raise ValueError(
                        f'Expected global configs attribute: {target_attr}. '
                        f'Cannot replace {to_replace} in invocation template'
                    )
                                
                json_str = replace(
                    json_str,
                    to_replace,
                    replacement,
                )

        return json_str
        
    def run_bosh_command(self, args: Sequence):
        args = [str(arg) for arg in args]
        command = f'bosh({args})'
        self.log_command(command)
        if not self.dry_run:
            bosh(args)
        self.command_history.append(command)
