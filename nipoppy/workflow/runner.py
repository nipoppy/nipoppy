import datetime
import json
import logging
import os
import re
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from nipoppy.base import GlobalConfigs

class BaseRunner(ABC):

    log_format = '%(asctime)s - %(name)s - %(levelname)s\t- %(message)s'

    singularity_bind_flag = '--bind'
    singularity_bind_sep = ':'
    
    def __init__(self, name: str, global_configs, logger=None, log_level=logging.DEBUG, dry_run=False) -> None:

        self.global_configs = GlobalConfigs(global_configs)
        self.name = name
        self.dry_run = dry_run
        self._logger = logger
        self.log_level = log_level

        self.fpath_log = None
        self.command_failed = False
        self.command_history = []
        self._singularity_flags = []

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            if self.fpath_log is None:
                self.fpath_log = self.generate_fpath_log(self.global_configs, self.name)
            self._logger = self.create_logger(
                name=str(self),
                fpath=self.fpath_log,
                level=self.log_level,
            )
        return self._logger

    def run(self, **kwargs):
        self.run_setup(**kwargs)
        self.run_main(**kwargs)
        self.run_cleanup(**kwargs)

    def run_setup(self, **kwargs):
        self.info('========== BEGIN ==========')

    @abstractmethod
    def run_main(self, **kwargs):
        pass

    def run_cleanup(self, **kwargs):
        self.info('========== END ==========')
    
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
    
    def generate_fpath_log(self, global_configs: GlobalConfigs, name, tags=None, sep_tag='-') -> Path:
        if tags is None:
            tags = []
        elif isinstance(tags, str):
            tags = [tags]
        tags = [str(tag) for tag in tags]
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dpath_log = global_configs.dpath_scratch / 'logs' / name # TODO don't hardcode path to scratch
        fname_log = f'{sep_tag.join([name, timestamp] + tags)}.log'
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
                self.command_failed = True
                raise exception

        # only include successful commands in history
        self.command_history.append(command_or_args)

        if not self.dry_run:
            return process
        else:
            return command
    
    @property
    def singularity_flags(self) -> str:
        return shlex.join(self._singularity_flags)

    def add_singularity_bind_flag(self, path_local: str | os.PathLike, path_container: str | os.PathLike | None = None, mode: str = 'rw'):
        if path_container is None:
            path_container = path_local
        self._singularity_flags.extend([
            self.singularity_bind_flag,
            self.singularity_bind_sep.join([str(path_local), str(path_container), mode])
        ])
        self.run_command(f'mkdir -p {path_local}')

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

    def __init__(self, name, global_configs, n_jobs=1, **kwargs) -> None:
        super().__init__(name, global_configs, **kwargs)
        self.n_jobs = n_jobs

    def run_setup(self, **kwargs):
        # TODO call get_args_for_parallel to get list of kwarg dicts
        # TODO validate list of kwarg dicts
        pass

    def run_main(self, **kwargs):
        if self.n_jobs == 1:
            # TODO loop over args
            return self.to_run_in_parallel(**kwargs)
        else:
            pass # TODO

    @abstractmethod
    def get_kwargs_for_parallel(self, **kwargs):
        pass

    @abstractmethod
    def to_run_in_parallel(self, **kwargs):
        pass

class BoutiquesRunner(BaseRunner):

    json_replace_pattern = re.compile('\[\[NIPOPPY\_(.*?)\]\]')
    dpath_descriptors = Path(__file__).parent / 'descriptors' # TODO don't hardcode path?

    def __init__(self, global_configs, pipeline_name: str, pipeline_version: str | None = None, **kwargs) -> None:
        super().__init__(pipeline_name, global_configs, **kwargs)
        self.pipeline_name = pipeline_name
        self.pipeline_version = self.global_configs.check_version(
            self.pipeline_name,
            pipeline_version,
        )
        self.descriptor_template: str = self.load_descriptor_template()
        self.invocation_template: str = self.load_invocation_template()

    @property
    def fpath_container(self) -> Path:
        return self.global_configs.get_fpath_container(
            self.pipeline_name,
            self.pipeline_version,
        )

    # TODO when to do validation (file exists, processing success)
    def load_descriptor_template(self) -> str:
        fpath_descriptor_template = self.dpath_descriptors / f'{self.pipeline_name}-{self.pipeline_version}.json'
        with fpath_descriptor_template.open() as file:
            descriptor_template = json.load(file)
        return json.dumps(descriptor_template)

    def load_invocation_template(self) -> str:
        fpath = self.global_configs.get_fpath_invocation_template(
            self.pipeline_name,
            self.pipeline_version,
        )

        with fpath.open() as file:
            invocation_template = json.load(file)
        return json.dumps(invocation_template)

    def run_main(self, **kwargs):

        # process and validate the descriptor
        descriptor = self.process_boutiques_json(self.descriptor_template)
        self.run_command(['bosh', 'validate', descriptor])

        # process and validate the invocation
        invocation = self.process_boutiques_json(
            self.invocation_template,
            **kwargs,
        )
        self.run_command(['bosh', 'invocation', '-i', invocation, descriptor])

        # run
        self.run_command(['bosh', 'exec', 'simulate', '-i', invocation, descriptor])
        self.run_command(['bosh', 'exec', 'launch', '--stream', descriptor, invocation])

    def process_boutiques_json(self, json_str: str, **kwargs) -> str:

        def replace(json_str: str, to_replace: str, replacement):
            return json_str.replace(to_replace, str(replacement))

        matches = self.json_replace_pattern.finditer(json_str)
        for match in matches:
            if len(match.groups()) != 1:
                raise ValueError(
                    f'Expected exactly one match group for match: {match}'
                )
            to_replace = match.group()
            replacement_key = match.groups()[0].lower()

            if replacement_key in kwargs:
                json_str = replace(json_str, to_replace, kwargs[replacement_key])
            elif hasattr(self, replacement_key):
                json_str = replace(json_str, to_replace, getattr(self, replacement_key))
            elif hasattr(self.global_configs, replacement_key):
                json_str = replace(json_str, to_replace, getattr(self.global_configs, replacement_key))
            else:
                raise RuntimeError(f'Unable to replace {to_replace} in {json_str}')
            
        return json_str
       
    def __str__(self) -> str:
        return self._str_helper([self.pipeline_name, self.pipeline_version])

class ProcpipeRunner(BoutiquesRunner):

    def __init__(self, global_configs, pipeline_name: str, pipeline_version: str | None = None, **kwargs) -> None:
        super().__init__(global_configs=global_configs, pipeline_name=pipeline_name, pipeline_version=pipeline_version, **kwargs)

    def run(self, subject: str, session: str, **kwargs):
        return super().run(subject=subject, session=session, **kwargs)
    
    def run_setup(self, subject: str, session: str, sep_tag='-', **kwargs):
        
        # overwrite log path
        # need to do this before calling super().run_setup
        self.fpath_log = self.generate_fpath_log(
            self.global_configs,
            self.name,
            tags=[subject, session],
            sep_tag=sep_tag,
        )

        super().run_setup(**kwargs)

        self.dpath_subject_session_work = (self.dpath_pipeline_work / sep_tag.join([subject, session])).resolve()

        self.add_singularity_bind_flag(self.global_configs.dpath_bids, mode='ro')   # input
        self.add_singularity_bind_flag(self.dpath_pipeline_output)                  # output
        self.add_singularity_bind_flag(self.dpath_subject_session_work)             # work
        self.add_singularity_bind_flag(self.dpath_bids_db)                          # pyBIDS
    
    def run_cleanup(self, **kwargs):

        try:
            dpath_subject_session_work = self.dpath_subject_session_work
        except AttributeError:
            raise RuntimeError(
                'dpath_subject_session_work not defined. '
                'run_setup must be run before run_cleanup.'
            )
        
        # delete temporary working directory if no command failed
        if not self.command_failed:
            self.run_command(f'rm -rf {dpath_subject_session_work}')

        super().run_cleanup(**kwargs)
    
    @property
    def dpath_pipeline_derivatives(self) -> Path:
        return self.global_configs.get_dpath_pipeline_derivatives(
            self.pipeline_name, self.pipeline_version
        ).resolve()
    
    @property
    def dpath_pipeline_output(self) -> Path:
        return (self.dpath_pipeline_derivatives / 'output').resolve()
    
    @property
    def dpath_pipeline_work(self) -> Path:
        return (self.dpath_pipeline_derivatives / 'work').resolve()

    @property
    def dpath_bids_db(self) -> Path:
        return (self.global_configs.dpath_proc / 'bids_db').resolve()
