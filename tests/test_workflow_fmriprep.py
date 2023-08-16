from nipoppy.workflow.proc_pipe.fmriprep.run_fmriprep import run_fmriprep

import nipoppy.workflow.logger as my_logger

def test_run_fmriprep():
    
    use_bids_filter = False
    anat_only = False
    log_file = "fmriprep.log"

    CMD = run_fmriprep(participant_id='01', 
                 bids_dir="bids_dir",
                 fmriprep_dir="fmriprep_dir",
                 fs_dir="fs_dir",
                 templateflow_dir="templateflow_dir",
                 SINGULARITY_CONTAINER="fmriprep.simg",
                 use_bids_filter=use_bids_filter,
                 anat_only=anat_only,
                 logger=my_logger.get_logger(log_file=log_file))
    
    assert CMD == [
        'singularity', 'run', 
            '-B', 'bids_dir:/data_dir', 
            '-B', 'fmriprep_dir/output//fmriprep_home_01/:/home/fmriprep', 
            '--home', '/home/fmriprep', 
            '--cleanenv', 
            '-B', 'fmriprep_dir/output/:/output', 
            '-B', 'templateflow_dir:/templateflow', 
            '-B', 'fmriprep_dir:/work', 
            '-B', 'fs_dir:/fsdir/', 
                'fmriprep.simg', '/data_dir', '/output', 'participant', 
                    '--participant-label', '01', 
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