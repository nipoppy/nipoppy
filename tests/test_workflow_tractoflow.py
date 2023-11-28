from __future__ import annotations

import logging
from pathlib import Path

import pytest

import nipoppy.workflow.logger as my_logger
from nipoppy.workflow.proc_pipe.tractoflow.run_tractoflow import run

from .conftest import global_config_for_testing, mock_bids_dataset, create_dummy_bids_filter


@pytest.mark.parametrize("use_bids_filter", [True, False])
def test_run(caplog, tmp_path, use_bids_filter):
    """Check that a logging error is raised."""

    caplog.set_level(logging.CRITICAL)

    if use_bids_filter:
        create_dummy_bids_filter(tmp_path / "proc", filename="bids_filter_tractoflow.json")

    output_dir = tmp_path
    log_file = tmp_path / "tractoflow.log"
    logger = my_logger.get_logger(log_file)

    global_configs = global_config_for_testing(tmp_path)

    bids_dir = Path(global_configs["DATASET_ROOT"]) / "bids"

    mock_bids_dataset(pth=bids_dir, dataset="ds004097")

    participant_id = "NDARDD890AYU"
    session_id = "01"

    CMD = run(
        participant_id=f"sub-{participant_id}",
        global_configs=global_configs,
        session_id=session_id,
        output_dir=output_dir,
        use_bids_filter=use_bids_filter,
        dti_shells="1000",
        fodf_shells="1000",
        sh_order=6,
        logger=logger,
    )

    expected_cmd = (
        f"nextflow run {tmp_path}/workflow/proc_pipe/tractoflow/tractoflow/main.nf "
        "-with-singularity tractoflow_XX.X.X.sif "
        f"-work-dir {tmp_path}/tractoflow/vXX.X.X/work/sub-{participant_id} "
        f"-with-trace {tmp_path}/scratch/logs/sub-{participant_id}_ses-{session_id}_nf-trace.txt "
        f"-with-report {tmp_path}/scratch/logs/sub-{participant_id}_ses-{session_id}_nf-report.html "
        f"--input {tmp_path}/tractoflow/vXX.X.X/input/norpe "
        f"--output_dir {tmp_path}/tractoflow/vXX.X.X/output/ "
        f'--participant-label "{participant_id}" '
        '--dti_shells "0 1000" '
        '--fodf_shells "0 1000" '
        "--sh_order 6 "
        "--profile fully_reproducible "
        "--processes 4"
    )

    assert CMD == expected_cmd
