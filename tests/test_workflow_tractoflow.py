from __future__ import annotations

import logging
from pathlib import Path

import pytest

import nipoppy.workflow.logger as my_logger
import nipoppy.workflow.proc_pipe.tractoflow.run_tractoflow as tractoflow_module
from nipoppy.workflow.proc_pipe.tractoflow.run_tractoflow import run

from .conftest import (
    _create_dummy_bids_filter,
    _delete_dummy_bids_filter,
    _global_config_for_testing,
    _mock_bids_dataset,
)


def _dummy_bids_filter_pth() -> Path:
    """TODO probably don't want the bids filter file to be in the module directory"""
    return Path(tractoflow_module.__file__).parent


@pytest.mark.parametrize("use_bids_filter", [True, False])
def test_run(caplog, tmp_path, use_bids_filter):
    """Check that a logging error is raised."""

    caplog.set_level(logging.CRITICAL)

    # TODO because this is set up and torn down after each test
    # we probably want to turn this into fixture
    _create_dummy_bids_filter(_dummy_bids_filter_pth())

    output_dir = tmp_path
    log_file = tmp_path / "tractoflow.log"
    logger = my_logger.get_logger(log_file)

    global_configs = _global_config_for_testing(tmp_path)

    bids_dir = Path(global_configs["DATASET_ROOT"]) / "bids"

    _mock_bids_dataset(pth=bids_dir, dataset="ds004097")

    participant_id = "sub-NDARDD890AYU"
    session_id = "01"

    run(
        participant_id=participant_id,
        global_configs=global_configs,
        session_id=session_id,
        output_dir=output_dir,
        use_bids_filter=use_bids_filter,
        dti_shells="1000",
        fodf_shells="1000",
        sh_order=6,
        logger=logger,
    )

    _delete_dummy_bids_filter(_dummy_bids_filter_pth())
