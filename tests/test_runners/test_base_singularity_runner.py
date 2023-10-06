import pytest

from nipoppy.workflow.runner import BaseSingularityRunner

from utils import global_configs_fixture

@pytest.fixture(scope='function')
def runner(global_configs_fixture, dpath_tmp):
    class DummyRunner(BaseSingularityRunner):
        def run_main(self, **kwargs):
            return
    runner = DummyRunner(global_configs_fixture, 'runner', dry_run=True)
    runner.fpath_log = dpath_tmp / 'runner.log'
    return runner

def test(runner: BaseSingularityRunner):
    assert runner
