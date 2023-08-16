from __future__ import annotations
import json
from pathlib import Path

import pytest

import nipoppy.workflow.logger as my_logger
from nipoppy.workflow.proc_pipe.fmriprep.run_fmriprep import run, run_fmriprep
import nipoppy.workflow.logger as my_logger


def global_config_file()-> Path:
    return Path(__file__).parent / "data" / "test_global_configs.json"


def global_config_for_testing() -> dict:
    with open(global_config_file(), 'r') as f:
        global_configs = json.load(f)
    return global_configs

def create_dummy_fs_license(pth: Path) -> None:
    pth = pth / "freesurfer"
    pth.mkdir(parents=True, exist_ok=True)
    license_file = pth / "license.txt"
    license_file.write_text("dummy content")


def test_run(tmp_path):

    log_file = tmp_path / "fmriprep.log"
    logger = my_logger.get_logger(log_file)

    create_dummy_fs_license(tmp_path)

    participant_id = "01"

    session_id = "01"

    run(
        participant_id=participant_id,
        global_configs=global_config_for_testing(),
        session_id=session_id,
        output_dir=tmp_path,
        use_bids_filter=False,
        anat_only=False,
        logger=logger
    )


@pytest.mark.parametrize("use_bids_filter", [True, False])
@pytest.mark.parametrize("anat_only", [True, False])
def test_run_fmriprep(tmp_path, use_bids_filter, anat_only):
    log_file = tmp_path / "fmriprep.log"

    bids_dir = "bids_dir"
    fmriprep_dir = "fmriprep_dir"
    fs_dir = "fs_dir"
    templateflow_dir = "templateflow_dir"
    participant_id = "01"
    singularity_container = "fmriprep.simg"

    cmd = run_fmriprep(
        participant_id=participant_id,
        bids_dir=bids_dir,
        fmriprep_dir=fmriprep_dir,
        fs_dir=fs_dir,
        templateflow_dir=templateflow_dir,
        SINGULARITY_CONTAINER=singularity_container,
        use_bids_filter=use_bids_filter,
        anat_only=anat_only,
        logger=my_logger.get_logger(log_file=log_file),
    )
    # fmt: off
    expected_cmd = [
        'singularity', 'run', 
            '-B', f'{bids_dir}:/data_dir', 
            '-B', f'{fmriprep_dir}/output//fmriprep_home_{participant_id}/:/home/fmriprep', 
            '--home', '/home/fmriprep', 
            '--cleanenv', 
            '-B', f'{fmriprep_dir}/output/:/output', 
            '-B', f'{templateflow_dir}:/templateflow', 
            '-B', f'{fmriprep_dir}:/work', 
            '-B', f'{fs_dir}:/fsdir/', 
                singularity_container, '/data_dir', '/output', 'participant', 
                    '--participant-label', participant_id, 
                    '-w', '/work', 
                    '--output-spaces', 'MNI152NLin2009cAsym:res-2', 'anat', 'fsnative', 
                    '--fs-subjects-dir', '/fsdir/', 
                    '--skip_bids_validation', 
                    '--bids-database-dir', '/work/first_run/bids_db/', 
                    '--fs-license-file', '/fsdir/license.txt', 
                    '--return-all-components', 
                    '-v', 
                    '--write-graph', 
                    '--notrack', 
                    '--omp-nthreads', '4', 
                    '--nthreads', '8', 
                    '--mem_mb', '4000']
    # fmt: on

    if use_bids_filter:
        expected_cmd += ["--bids-filter-file", "/data_dir/bids_filter.json"]

    if anat_only:
        expected_cmd += ["--anat-only"]

    assert cmd == expected_cmd
