import logging
from pathlib import Path

import pytest
from nipoppy.logger import create_logger

from conftest import dpath_tmp

@pytest.mark.parametrize('fpath', [None, 'test.log'])
def test_create_logger(fpath, dpath_tmp, caplog: pytest.LogCaptureFixture):
    if fpath is not None:
        fpath = dpath_tmp / fpath
    assert isinstance(create_logger('test', fpath), logging.Logger)
    if fpath is not None:
        assert str(fpath) in caplog.text
    else:
        assert 'will not write to a log file' in caplog.text

def test_create_logger_set_fpath(dpath_tmp: Path):
    fpath_log = dpath_tmp / 'test.log'
    if fpath_log.exists():
        fpath_log.unlink()
    assert isinstance(create_logger('test', fpath_log), logging.Logger)
    assert fpath_log.exists()
