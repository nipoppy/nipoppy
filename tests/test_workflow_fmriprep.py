import pytest

from nipoppy.workflow.proc_pipe.fmriprep.run_fmriprep import run_fmriprep

import nipoppy.workflow.logger as my_logger

@pytest.mark.parametrize("use_bids_filter", [True, False])
@pytest.mark.parametrize("anat_only", [True, False])
def test_run_fmriprep(use_bids_filter, anat_only):
    
    log_file = "fmriprep.log"

    bids_dir="bids_dir"
    fmriprep_dir = "fmriprep_dir"
    fs_dir="fs_dir"
    templateflow_dir="templateflow_dir"
    participant_id = '01'
    singularity_container="fmriprep.simg"

    cmd = run_fmriprep(participant_id=participant_id, 
                 bids_dir=bids_dir,
                 fmriprep_dir=fmriprep_dir,
                 fs_dir=fs_dir,
                 templateflow_dir=templateflow_dir,
                 SINGULARITY_CONTAINER=singularity_container,
                 use_bids_filter=use_bids_filter,
                 anat_only=anat_only,
                 logger=my_logger.get_logger(log_file=log_file))
    
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

    if use_bids_filter:
        expected_cmd += ['--bids-filter-file', '/data_dir/bids_filter.json']

    if anat_only:
        expected_cmd += ['--anat-only']

    assert cmd == expected_cmd