import os
import subprocess
from abc import ABC, abstractmethod
from typing import Sequence

from boutiques import bosh

# TODO add logger

class BaseRunner():
    
    def __init__(self, global_config, dry_run=False) -> None:
        if isinstance(global_config, (str, os.PathLike)):
            pass # TODO load global_config
        self.global_config = global_config
        self.dry_run = dry_run

    def run(self, *args, **kwargs):
        self.run_setup(*args, **kwargs)
        self.run_main(*args, **kwargs)
        self.run_cleanup(*args, **kwargs)

    def run_setup(self, *args, **kwargs):
        pass

    def run_main(self, *args, **kwargs):
        pass

    def run_cleanup(self, *args, **kwargs):
        pass

    def _run_command(self, command: Sequence[str] | str):

        # build command string
        if not isinstance(command, str):
            command = ' '.join([str(arg) for arg in command])

        # TODO print/log command string

        if not self.dry_run:
            # TODO throw error on fail
            subprocess_result = subprocess.run(command.split())

        return subprocess_result

class ParallelRunner(BaseRunner, ABC):

    def __init__(self, global_config, n_jobs=1) -> None:
        super().__init__(global_config)
        self.n_jobs = n_jobs

    def run_main(self, *args, **kwargs):
        if self.n_jobs == 1:
            return self.to_run_in_parallel(*args, **kwargs)
        else:
            pass # TODO

    @abstractmethod
    def to_run_in_parallel(self, *args, **kwargs):
        pass

class BoutiquesRunner(BaseRunner):

    def __init__(self, global_config, pipeline_name, pipeline_version=None) -> None:
        super().__init__(global_config)
        self.pipeline_name: str = pipeline_name
        self.pipeline_version: str = pipeline_version

        # TODO check that boutiques/bosh is installed

        self.descriptor: str = self.load_and_validate_descriptor()
        self.invocation: str = None # TODO get Boutiques invocation (from global configs)

    def load_and_validate_descriptor(self):
        descriptor = None # TODO load Boutiques descriptor (from code repo)
        bosh(["validate", descriptor])
        return descriptor

    def run_setup(self, subject, session, invocation, *args, **kwargs):

        # TODO
        # load invocation JSON
        # inject subject/session (run?)
        # validate the invocation
        # save invocation as attribute
        pass

    def run_main(self, *args, **kwargs):
        if self.descriptor is None:
            raise RuntimeError("No descriptor")
        if self.invocation is None:
            raise RuntimeError("No invocation")
        # TODO run it (bosh execute launch [descriptor] [invocation])


# class TestRunner(BoutiquesRunner):
    
#     def run_main(self, subject, session, invocation, *args, **kwargs):
#         print("Running test pipeline")

# if __name__ == "__main__":
#     runner = TestRunner(None)
#     print(runner.pipeline_name)

