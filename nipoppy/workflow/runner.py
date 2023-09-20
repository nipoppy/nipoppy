import datetime
import json
import logging
import os
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

import boutiques

from nipoppy.base import GlobalConfigs

class BaseRunner(ABC):

    log_format = '%(asctime)s - %(name)s - %(levelname)s\t- %(message)s'
    
    def __init__(self, name: str, global_configs: GlobalConfigs | str | os.PathLike | dict, logger=None, log_level=logging.DEBUG, dry_run=False) -> None:

        if isinstance(global_configs, (str, os.PathLike, dict)):
            global_configs = GlobalConfigs(global_configs)

        fpath_log = self.generate_fpath_log(global_configs, name)
        if logger is None:
            logger = self.create_logger(
                name=str(self),
                fpath=fpath_log,
                level=log_level,
            )

        self.name = name
        self.dry_run = dry_run
        self.global_configs = global_configs
        self.logger = logger
        self.log_level = log_level
        self.fpath_log = fpath_log
        self.command_history = []

    def run(self, *args, **kwargs):
        self.info('========== BEGIN ==========')
        self.run_setup(*args, **kwargs)
        self.run_main(*args, **kwargs)
        self.run_cleanup(*args, **kwargs)
        self.info('========== END ==========')

    def run_setup(self, *args, **kwargs):
        return

    @abstractmethod
    def run_main(self, *args, **kwargs):
        pass

    def run_cleanup(self, *args, **kwargs):
        return
    
    @classmethod
    def create_logger(cls, name: str, fpath=None, level=logging.DEBUG) -> logging.Logger:
        
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # always output to terminal
        stream_handler = logging.StreamHandler()
        stream_formatter = logging.Formatter(cls.log_format)
        stream_handler.setFormatter(stream_formatter)
        logger.addHandler(stream_handler)

        # output to file if fpath is provided
        if fpath is not None:

            fpath = Path(fpath)
            fpath.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(fpath)
            file_formatter = logging.Formatter(cls.log_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger
    
    def generate_fpath_log(self, global_configs: GlobalConfigs, name) -> Path:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dpath_log = global_configs.dataset_root / 'scratch' / 'logs' / name # TODO don't hardcode path to scratch
        fname_log = f'{name}-{timestamp}.log'
        return dpath_log / fname_log

    def run_commands(self, seq_of_commands_or_args: Sequence[Sequence[str] | str]):
        for command in seq_of_commands_or_args:
            self.run_command(command)

    def run_command(self, command_or_args: Sequence[str] | str, check=True, **kwargs):

        # build command string
        if not isinstance(command_or_args, str):
            args = [str(arg) for arg in command_or_args]
            command = shlex.join(args)
        else:
            command = command_or_args
            args = shlex.split(command)

        self.log_command(command)

        if not self.dry_run:

            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            while process.poll() is None:
                for line in process.stdout:
                    line = line.strip('\n')
                    self.debug(f'[RUN OUTPUT] {line}')

            if check and process.returncode != 0:
                exception = subprocess.CalledProcessError(process.returncode, command)
                self.error(exception)
                raise exception

        # only include successful commands in history
        self.command_history.append(command_or_args)

        return process
    
    def log_command(self, command: str):
        self.info(f'[RUN] {command}')
    
    def log(self, message, level=logging.INFO):
        self.logger.log(level, message)

    def info(self, message):
        return self.log(message, level=logging.INFO)

    def debug(self, message):
        return self.log(message, level=logging.DEBUG)
    
    def error(self, message):
        return self.log(message, level=logging.ERROR)

    def _str_helper(self, components=None, names=None, sep=', '):
        if components is None:
            components = []

        if names is not None:
            for name in names:
                components.append(f'{name}={getattr(self, name)}')
        return f'{type(self).__name__}({sep.join([str(c) for c in components])})'

    def __str__(self) -> str:
        return self._str_helper()

    def __repr__(self) -> str:
        return self.__str__()

class BaseParallelRunner(BaseRunner, ABC):

    def __init__(self, name, global_configs, n_jobs=1, *args, **kwargs) -> None:
        super().__init__(name, global_configs, *args, **kwargs)
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
        global_configs = GlobalConfigs(global_configs)
        self.pipeline_name = pipeline_name
        self.pipeline_version = global_configs.check_version(
            self.pipeline_name,
            pipeline_version,
        )
        super().__init__(pipeline_name, global_configs, *args, **kwargs)

        self.descriptor = self.load_descriptor()
        self.invocation_template: str = self.load_invocation_template()

    def load_descriptor(self) -> str:
        fpath_descriptor_template = self.dpath_descriptors / f'{self.pipeline_name}-{self.pipeline_version}.json'
        with fpath_descriptor_template.open() as file:
            descriptor_template = json.load(file)
        descriptor_template = self.process_boutiques_json(json.dumps(descriptor_template))
        return descriptor_template

    def load_invocation_template(self) -> str:
        fpath = self.global_configs.get_fpath_invocation_template(
            self.pipeline_name,
            self.pipeline_version,
        )

        with fpath.open() as file:
            invocation_template = json.load(file)
        return json.dumps(invocation_template)
    
    def run(self, subject=None, session=None, *args, **kwargs):
        return super().run(subject=subject, session=session, *args, **kwargs)

    def run_main(self, *args, **kwargs):
        return self._run_boutiques(*args, **kwargs)

    def _run_boutiques(self, *args, **kwargs):

        self.run_command(['bosh', 'validate', self.descriptor])

        invocation = self.process_boutiques_json(
            self.invocation_template,
            *args,
            **kwargs,
        )

        try:
            self.run_command(
                ['bosh', 'invocation', '-i', invocation, self.descriptor],
            )
        except boutiques.invocationSchemaHandler.InvocationValidationError:
            raise RuntimeError(
                f'Invalid invocation {invocation}'
            )

        self.run_command(['bosh', 'exec', 'simulate', '-i', invocation, self.descriptor])
        self.run_command(['bosh', 'exec', 'launch', '--stream', self.descriptor, invocation])

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
        
    def __str__(self) -> str:
        return self._str_helper([self.pipeline_name, self.pipeline_version])
