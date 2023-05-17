import argparse
import json
import subprocess
import os
from pathlib import Path
import workflow.logger as my_logger
import shutil
#import re
#import glob
from bids import BIDSLayout

#Author: bcmcpher
#Date: 14-Apr-2023 (last update)
fname = __file__
CWD = os.path.dirname(os.path.abspath(fname))

# env vars relative to the container.

MEM_MB = 4000

def parse_data(bids_dir, participant_id, session_id, logger):
    """ Parse and verify the input files to build TractoFlow's simplified input to avoid their custom BIDS filter
    """

    ## because why parse subject ID the same as bids ID?
    subj = participant_id.replace('sub-', '')
    
    ## parse directory
    layout = BIDSLayout(bids_dir)

    ## pull every t1w / dwi file name from BIDS layout
    anat_files = layout.get(subject=subj, session=session_id, suffix='T1w', extension='.nii.gz', return_type='object')
    dmri_files = layout.get(subject=subj, session=session_id, suffix='dwi', extension='.nii.gz', return_type='object')

    ## anat parsing
    tamet = []
    tanat = []
    
    print("Parsing Anatomical Files...")
    for idx, anat in enumerate(anat_files):

        ## pull the data
        tamet.append(anat.get_metadata())
        tanat.append(anat.get_image())

        print("- - - - - - - - - -")
        print(anat.filename)
        print(f"Scan Type: {tamet[idx]['MatrixCoilMode']}\nData Shape: {tanat[idx].shape}")
        print(f"File has: {len(anat.get_entities()} parts")
        
    print("- - - - - - - - - -")
    
    ## default to most generic name?
    ##  - check sidecar - what obvious fields can exclude a file?
    ##  - SENSE vs. GRAPPA?

    ## dwi parsing - check phase encoding dir
    dmri_files = layout.get(subject=subj, session=session_id, suffix='dwi', PhaseEncodingDirection='j', return_type='object')
    dmri_files = layout.get(subject=subj, session=session_id, suffix='dwi', PhaseEncodingDirection='j-', return_type='object')
    ## check acquisition dir from sidecar to determine file to create (average) into rev_b0
    ##  - create rev_b0

    ## do some stuff...

    ## if rpe_file is made, it needs to be uniquely names in tmp before it is copied (moved?) to input_dir
    
    ## return the paths to the input files to copy
    return(dmrifile, bvalfile, bvecfile, anatfile, rpe_file)

def run_tractoflow(participant_id, global_configs, session_id, output_dir, use_bids_filter, logger=None):
    """ Runs TractoFlow command with Nextflow
    """

    ## extract the config options
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    CONTAINER_STORE = global_configs["CONTAINER_STORE"]
    TRACTOFLOW_CONTAINER = global_configs["PROC_PIPELINES"]["tractoflow"]["CONTAINER"]
    TRACTOFLOW_VERSION = global_configs["PROC_PIPELINES"]["tractoflow"]["VERSION"]
    TRACTOFLOW_CONTAINER = TRACTOFLOW_CONTAINER.format(TRACTOFLOW_VERSION)
    SINGULARITY_TRACTOFLOW = f"{CONTAINER_STORE}{TRACTOFLOW_CONTAINER}"
    LOGDIR = f"{DATASET_ROOT}/scratch/logs"

    ## initialize the logger
    if logger is None:
        log_file = f"{LOGDIR}/{participant_id}_ses-{session_id}_tractoflow.log"
        logger = my_logger.get_logger(log_file)

    ## log the info
    logger.info("-"*75)
    logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    logger.info(f"Using participant_id: {participant_id}, session_id: {session_id}")

    ## define default output_dir if it's not overwrote
    if output_dir is None:
        output_dir = f"{DATASET_ROOT}/derivatives"

    ## build paths to files
    bids_dir = f"{DATASET_ROOT}/bids"
    tractoflow_dir = f"{output_dir}/tractoflow/v{TRACTOFLOW_VERSION}"

    ## Copy bids_filter.json `<DATASET_ROOT>/bids/bids_filter.json`
    if use_bids_filter:
        logger.info(f"Copying ./bids_filter.json to {DATASET_ROOT}/bids/bids_filter.json (to be seen by Singularity container)")
        shutil.copyfile(f"{CWD}/bids_filter.json", f"{bids_dir}/bids_filter.json")

    ## build paths for outputs
    tractoflow_out_dir = f"{tractoflow_dir}/output/"
    tractoflow_home_dir = f"{tractoflow_out_dir}/{participant_id}"
    if not os.path.exists(Path(f"{tractoflow_home_dir}")):
        Path(f"{tractoflow_home_dir}").mkdir(parents=True, exist_ok=True)

    ## build paths for working inputs
    tractoflow_input_dir = f"{tractoflow_dir}/input"
    tractoflow_subj_dir = f"{tractoflow_input_dir}/{participant_id}"
    tractoflow_work_dir = f"{tractoflow_dir}/work/{participant_id}"

    if not os.path.exists(Path(f"{tractoflow_subj_dir}")):
        Path(f"{tractoflow_subj_dir}").mkdir(parents=True, exist_ok=True)

    if not os.path.exists(Path(f"{tractoflow_work_dir}")):
        Path(f"{tractoflow_work_dir}").mkdir(parents=True, exist_ok=True)

    ## call the file parser to copy the correct files to the input structure
    dmrifile, bvalfile, bvecfile, anatfile, rpe_file = parse_data(bids_dir, participant_id, session_id, run_id, logger)
        
    # ## copy the bids data into this folder in their "simple" input structure b/c bids parsing doesn't work
    # ## and uses a unique filter that isn't easy / worth parsing
    # dmrifile = f"{bids_dir}/{participant_id}/ses-{session_id}/dwi/{participant_id}_ses-{session_id}_run-1_dwi.nii.gz"  ## bad path generalization for now.
    # bvalfile = f"{bids_dir}/{participant_id}/ses-{session_id}/dwi/{participant_id}_ses-{session_id}_run-1_dwi.bval"    ## not trivial to parse and build
    # bvecfile = f"{bids_dir}/{participant_id}/ses-{session_id}/dwi/{participant_id}_ses-{session_id}_run-1_dwi.bvec"    ## the right names, esp. if bids
    # anatfile = f"{bids_dir}/{participant_id}/ses-{session_id}/anat/{participant_id}_ses-{session_id}_run-1_T1w.nii.gz" ## parsing isn't more helpful
    # #rpe_file = too hard to parse for now - too many valid names are possible for input.
    # ## will need to extract and average b0s after verifying the rpe is actually reversed by checking sidecar.

    ## just make copies if they aren't already there - resume option cannot work w/ modfied (recopied) files, so check first
    ## delete on success?
    if len(os.listdir(tractoflow_subj_dir)) == 0:
        shutil.copyfile(dmrifile, tractoflow_subj_dir + '/dwi.nii.gz')
        shutil.copyfile(bvalfile, tractoflow_subj_dir + '/bval')
        shutil.copyfile(bvecfile, tractoflow_subj_dir + '/bvec')
        shutil.copyfile(anatfile, tractoflow_subj_dir + '/t1.nii.gz')
        #shutil.copyfile(rpe_file, tractoflow_work_dir + '/rev_b0.nii.gz') # figure out how to make this if input doesn't match

    # ## cd to tractoflow_work_dir to control where the "work" folder ends up
    # os.chdir(tractoflow_work_dir)
    # logger.info(f"Setting working directory to: {tractoflow_work_dir}")

    ## drop sub- from participant ID
    tf_id = re.sub("sub-", "", participant_id)
    
    ## generalize as inputs - eventually
    dti_shells=1000
    fodf_shells=1000
    sh_order=6
    profile='fully_reproducible'
    ncore=4

    ## path to pipelines
    TRACTOFLOW_PIPE=f'{DATASET_ROOT}/workflow/proc_pipe/tractoflow'
    
    ## this is fixed for every run - nextflow is a dependency b/c it's too hard to package in the containers that will call this
    ## this reality prompts the planned migration to micapipe - or anything else, honestly
    NEXTFLOW_CMD=f"nextflow run {TRACTOFLOW_PIPE}/tractoflow/main.nf -with-singularity {SINGULARITY_TRACTOFLOW} -work-dir {tractoflow_work_dir} -with-trace {LOGDIR}/{participant_id}_ses-{session_id}_nf-trace.txt -with-report {LOGDIR}/{participant_id}_ses-{session_id}_nf-report.html"
    
    ## compose tractoflow arguments
    TRACTOFLOW_CMD=f""" --input {tractoflow_input_dir} --output_dir {tractoflow_out_dir} --participant-label "{tf_id}" --dti_shells "0 {dti_shells}" --fodf_shells "0 {fodf_shells}" --sh_order {sh_order} --profile {profile} --processes {ncore}"""

    ## I have no idea why the inputs have to be parsed this way. The TractoFlow arguments can be printed multiple ways that appear consistent with the documentation but are parsed incorrectly by nextflow.
    ## .nexflow.log (a run log that documents what is getting parsed by nexflow) shows additional quotes being added around the dti / fodf parameters. Something like: "'0' '1000'"
    ## Obviously, this breaks the calls that nextflow tries to make at somepoint (typically around Normalize_DWI) because half the command becomes an unfinished text block from the mysteriously added quotes.
    ## I don't know if the problem is python printing unhelpful/inaccurate text to the user or if nextflow can't parse its own input arguments correctly.
    
    ## add resume option if working directory is not empty
    if not len(os.listdir(tractoflow_work_dir)) == 0:
        TRACTOFLOW_CMD = TRACTOFLOW_CMD + " -resume"
    
    ## build command line call
    CMD_ARGS = NEXTFLOW_CMD + TRACTOFLOW_CMD 
    CMD=CMD_ARGS
    #CMD = CMD_ARGS.split()

    ## log what is called
    logger.info(f"Running TractoFlow...")
    logger.info("-"*50)
    logger.info(f"CMD:\n{CMD_ARGS}")
    logger.info("-"*50)
    logger.info(f"Calling TractoFlow for participant: {participant_id}")

    ## there's probably a better way to try / catch the .run() call here
    try:
        tractoflow_proc = subprocess.run(CMD, shell=True)
        logger.info("-"*75)
    except Exception as e:
        logger.error(f"TractoFlow run failed with exceptions: {e}")
        logger.info("-"*75)


if __name__ == '__main__':
    ## argparse
    HELPTEXT = """
    Script to run TractoFlow 
    """

    ## parse intputs
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset', required=True)
    parser.add_argument('--participant_id', type=str, help='participant id', required=True)
    parser.add_argument('--session_id', type=str, help='session id for the participant', required=True)
    parser.add_argument('--output_dir', type=str, default=None, help='specify custom output dir (if None --> <DATASET_ROOT>/derivatives)')
    parser.add_argument('--use_bids_filter', action='store_true', help='use bids filter or not')

    ## extract arguments
    args = parser.parse_args()
    global_config_file = args.global_config
    participant_id = args.participant_id
    session_id = args.session_id
    output_dir = args.output_dir # Needed on BIC (QPN) due to weird permissions issues with mkdir
    use_bids_filter = args.use_bids_filter

    ## Read global config
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    ## make valid tractoflow call based on inputs    
    run_tractoflow(participant_id, global_configs, session_id, output_dir, use_bids_filter)