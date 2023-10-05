import logging
import re
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from nipoppy.workflow.runner import BaseRunner

from utils import global_configs_fixture

@pytest.fixture
def runner(global_configs_fixture, dpath_tmp):
    class DummyRunner(BaseRunner):
        def run_main(self, **kwargs):
            return
    runner = DummyRunner(global_configs_fixture, 'runner', dry_run=True)
    runner.fpath_log = dpath_tmp / 'runner.log'
    return runner

@pytest.fixture
def dpath_tmp():
    return Path(__file__).parent / 'tmp'

@pytest.fixture(autouse=True)
def tmp_dir(dpath_tmp: Path):

    def remove_dir(dpath: Path):
        for subpath in dpath.iterdir():
            if subpath.is_dir():
                remove_dir(subpath)
            else:
                subpath.unlink()
        dpath.rmdir()

    dpath_tmp.mkdir(exist_ok=True)
    yield
    remove_dir(dpath_tmp)

def test_abstract_class():
    with pytest.raises(TypeError, match='Can\'t instantiate abstract class'):
        BaseRunner(None, None)

def test_log_errors(runner: BaseRunner, caplog):
    
    @BaseRunner.log_errors
    def my_func(self):
        raise Exception()
    
    with pytest.raises(Exception):
        my_func(runner)
    
    error_log_count = 0
    for record in reversed(caplog.records):
        if '=== END ===' in record.message:
            break
        if record.levelno == logging.ERROR:
            error_log_count += 1
    assert error_log_count > 1

def test_run(runner: BaseRunner):
    runner.run()

@pytest.mark.parametrize(
    'print_begin,substring',
    [(True, 'BEGIN'), (False, None)],
)
def test_run_setup(runner: BaseRunner, print_begin, substring, caplog):
    caplog.set_level(logging.DEBUG)
    runner.run_setup(print_begin=print_begin)
    if substring is None:
        assert caplog.text == ''
    else:
        assert substring in caplog.text

@pytest.mark.parametrize(
    'print_end,substring',
    [(True, 'END'), (False, None)],
)
def test_run_cleanup(runner: BaseRunner, print_end, substring, caplog):
    caplog.set_level(logging.DEBUG)
    runner.run_cleanup(print_end=print_end)
    if substring is None:
        assert caplog.text == ''
    else:
        assert substring in caplog.text

@pytest.mark.parametrize(
    'template_str,resolve_paths,kwargs,expected',
    [
        ('no_replace', False, {}, 'no_replace'),
        ('[[NIPOPPY_DNAME_LOGS]]', False, {}, 'logs'),
        ('[[NIPOPPY_DPATH_BIDS]]', False, {}, 'bids'),
        ('[[NIPOPPY_DPATH_BIDS]]', True, {}, Path('bids').resolve()),
        ('[[NIPOPPY_SOME_KWARG]]', False, {'some_kwarg': 'some_value'}, 'some_value'),
    ],
)
def test_process_template_str(runner: BaseRunner, template_str, resolve_paths, kwargs, expected):
    assert runner.process_template_str(template_str, resolve_paths, **kwargs) == str(expected)
    
def test_process_template_str_error_pattern(runner: BaseRunner):
    runner = deepcopy(runner)
    runner.template_replace_pattern = re.compile('\\[\\[NIPOPPY\\_(.*)\\_(.*)\\]\\]')
    with pytest.raises(ValueError, match='Expected exactly one match'):
        runner.process_template_str('[[NIPOPPY_SOME_KWARG]]')

def test_process_template_str_error_replace(runner: BaseRunner):
    with pytest.raises(RuntimeError, match='Unable to replace'):
        runner.process_template_str('[[NIPOPPY_INVALID]]')

@pytest.mark.parametrize('fpath', [None, 'test.log'])
def test_create_logger(fpath, dpath_tmp, caplog):
    if fpath is not None:
        fpath = dpath_tmp / fpath
    assert BaseRunner.create_logger('test', fpath)
    if fpath is not None:
        assert str(fpath) in caplog.text
    else:
        assert 'will not write to a log file' in caplog.text

@pytest.mark.parametrize(
    'tags,sep,substring',
    [
        (None, '-', 'runner'),
        ([3000], '-', '3000'),
        ([3000, 'BL'], '-', '3000-BL'),
        ([3000, 'BL'], '_', '3000_BL'),
    ],
)
def test_generate_fpath_log(runner: BaseRunner, tags, sep, substring):
    runner = deepcopy(runner)
    runner.sep = sep
    fpath = runner.generate_fpath_log(tags)
    assert runner.global_configs.dpath_scratch in fpath.parents
    assert runner.dname_logs in fpath.parts
    assert substring in str(fpath)

@pytest.mark.parametrize(
    'command_or_args,capture_output,expected',
    [
        ('echo x', False, 'echo x'),
        (['echo', 'y'], False, 'echo y'),
        ('echo x', True, 'x\n'),
        (['echo', 'y'], True, 'y\n'),
    ],
)
@pytest.mark.parametrize('check', [True, False])
def test_run_command(runner: BaseRunner, command_or_args, check, capture_output, expected):
    runner = deepcopy(runner)
    if capture_output:
        runner.dry_run = False
    assert expected == runner.run_command(command_or_args, check=check, capture_output=capture_output)

@pytest.mark.parametrize('prefix_run', ['[RUN]', '<run>'])
@pytest.mark.parametrize('prefix_run_output', ['[RUN OUTPUT]', '<run output>'])
def test_run_command_log(runner: BaseRunner, prefix_run, prefix_run_output, caplog):
    runner = deepcopy(runner)
    runner.dry_run = False
    runner.log_prefix_run = prefix_run
    runner.log_prefix_run_output = prefix_run_output
    runner.run_command('echo x')
    debug_log_count = 0
    for record in reversed(caplog.records):
        if record.levelno == logging.DEBUG:
            assert record.message.startswith(prefix_run_output)
            debug_log_count += 1
        elif record.levelno == logging.INFO:
            assert record.message.startswith(prefix_run)
            break
    assert debug_log_count > 0

def test_run_command_error(runner: BaseRunner):
    runner = deepcopy(runner)
    runner.dry_run = False
    with pytest.raises(subprocess.CalledProcessError, match='non-zero exit status'):
        runner.run_command('ls invalid_path', check=True)
    assert runner.command_failed

@pytest.mark.parametrize('command', ['echo x', 'echo y'])
@pytest.mark.parametrize('prefix_run', ['[RUN]', '<run>'])
def test_log_command(runner: BaseRunner, command, prefix_run, caplog):
    runner = deepcopy(runner)
    runner.log_prefix_run = prefix_run
    runner.log_command(command)
    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    assert record.message.startswith(prefix_run)
    assert command in record.message

@pytest.mark.parametrize('message', ['test', 'log'])
@pytest.mark.parametrize('level', [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL])
def test_log(runner: BaseRunner, message, level, caplog):
    runner._log(message, level=level)
    record = caplog.records[-1]
    assert record.levelno == level
    assert record.message == message

@pytest.mark.parametrize('level', ['debug', 'info', 'warning', 'error', 'critical'])
def test_log_levels(runner: BaseRunner, level, caplog):
    getattr(runner, level)('message')
    record = caplog.records[-1]
    assert record.levelname == level.upper()
