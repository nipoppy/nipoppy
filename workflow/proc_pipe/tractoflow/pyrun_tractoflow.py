import argparse
import json
import subprocess
import os
from pathlib import Path
import workflow.logger as my_logger
import shutil

#Author: bcmcpher
#Date: 14-Apr-2023 (last update)
fname = __file__
CWD = os.path.dirname(os.path.abspath(fname))

# env vars relative to the container.

MEM_MB = 4000

def run_tractoflow(participant_id, session_id, bids_dir, tractoflow_dir, SINGULARITY_CONTAINER, use_bids_filter, log_dir, logger):
    """ Launch fmriprep container"""

    tractoflow_out_dir = f"{tractoflow_dir}/output/"
    tractoflow_home_dir = f"{tractoflow_out_dir}/{participant_id}"
    Path(f"{tractoflow_home_dir}").mkdir(parents=True, exist_ok=True)

    ## generalize / code as inputs?
    dti_shells='"0 1000"'
    fodf_shells='"0 1000"'
    sh_order=6
    profile="fully_reproducible"
    ncore=4

    # path to pipelines - extract / pass from global_config.json or run()?
    MRPROC_PIPE='/data/origami/bcmcpher/git/mr_proc/workflow/proc_pipe/tractoflow'
    
    NEXTFLOW_CMD=f"nextflow run {MRPROC_PIPE}/tractoflow/main.nf"
    
    # Compose tractoflow command
    TRACTOFLOW_CMD=f" --bids {bids_dir} --output_dir {tractoflow_out_dir} participant --participant-label {participant_id} --dti-shells {dti_shells} --fodf_shells {fodf_shells} --sh_order {sh_order} --profile {profile} -with-singularity {SINGULARITY_CONTAINER} --processes {ncore} -with-trace {log_dir}/{participant_id}_ses-{session_id}_nf-tract.txt -with-report {log_dir}/{participant_id}_ses-{session_id}_nf-report.html -resume"
    
    CMD_ARGS = NEXTFLOW_CMD + TRACTOFLOW_CMD 
    #CMD = CMD_ARGS.split()
    CMD = CMD_ARGS

    ## "working" call?
    #nextflow run /data/origami/bcmcpher/git/mr_proc/workflow/proc_pipe/tractoflow/tractoflow/main.nf --bids /data/origami/bcmcpher/qpn-dev/bids/ --output_dir /data/origami/bcmcpher/test/tractoflow/v2.2.1/output/ participant --participant-label sub-MNI0056D864854 --dti_shells "0 1000" --fodf_shells "0 1000" --sh_order 6 --profile fully_reproducible -with-singularity /data/origami/container_store/mr_proc/tractoflow_2.2.1.sif --processes 4 -with-trace /data/origami/bcmcpher/qpn-dev/scratch/logs/sub-MNI0056D864854_ses-01_nf-tract.txt -with-report /data/origami/bcmcpher/qpn-dev/scratch/logs/sub-MNI0056D864854_ses-01_nf-report.html -resume
    
    logger.info(f"Running TractoFlow...")
    logger.info("-"*50)
    logger.info(f"CMD:\n{CMD}")
    logger.info("-"*50)
    try:
        tractoflow_proc = subprocess.run(CMD)
        logger.info(f"Successfully completed TractoFlow run for participant: {participant_id}")
        logger.info("-"*75)
    except Exception as e:
        logger.error(f"TractoFlow run failed with exceptions: {e}")
        logger.info("-"*75)
    logger.info("")

def run(participant_id, global_configs, session_id, output_dir, use_bids_filter, logger=None):
    """ Runs tractoflow command
    """
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    CONTAINER_STORE = global_configs["CONTAINER_STORE"]
    TRACTOFLOW_CONTAINER = global_configs["PROC_PIPELINES"]["tractoflow"]["CONTAINER"]
    TRACTOFLOW_VERSION = global_configs["PROC_PIPELINES"]["tractoflow"]["VERSION"]
    TRACTOFLOW_CONTAINER = TRACTOFLOW_CONTAINER.format(TRACTOFLOW_VERSION)

    SINGULARITY_TRACTOFLOW = f"{CONTAINER_STORE}{TRACTOFLOW_CONTAINER}"

    log_dir = f"{DATASET_ROOT}/scratch/logs"

    if logger is None:
        log_file = f"{log_dir}/{participant_id}_ses-{session_id}_tractoflow.log"
        logger = my_logger.get_logger(log_file)

    logger.info("-"*75)
    logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    logger.info(f"Using participant_id: {participant_id}, session_id: {session_id}")

    if output_dir is None:
        output_dir = f"{DATASET_ROOT}/derivatives/"

    bids_dir = f"{DATASET_ROOT}/bids/"
    tractoflow_dir = f"{output_dir}/tractoflow/v{TRACTOFLOW_VERSION}"

    # Copy bids_filter.json `<DATASET_ROOT>/bids/bids_filter.json`
    if use_bids_filter:
        logger.info(f"Copying ./bids_filter.json to {DATASET_ROOT}/bids/bids_filter.json (to be seen by Singularity container)")
        shutil.copyfile(f"{CWD}/bids_filter.json", f"{bids_dir}/bids_filter.json")

    # launch tractoflow
    run_tractoflow(participant_id, session_id, bids_dir, tractoflow_dir, SINGULARITY_TRACTOFLOW, use_bids_filter, log_dir, logger)

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to run tractoflow 
    """

    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset', required=True)
    parser.add_argument('--participant_id', type=str, help='participant id', required=True)
    parser.add_argument('--session_id', type=str, help='session id for the participant', required=True)
    parser.add_argument('--output_dir', type=str, default=None, help='specify custom output dir (if None --> <DATASET_ROOT>/derivatives)')
    parser.add_argument('--use_bids_filter', action='store_true', help='use bids filter or not')

    args = parser.parse_args()

    global_config_file = args.global_config
    participant_id = args.participant_id
    session_id = args.session_id
    output_dir = args.output_dir # Needed on BIC (QPN) due to weird permissions issues with mkdir
    use_bids_filter = args.use_bids_filter

    # Read global configs
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    run(participant_id, global_configs, session_id, output_dir, use_bids_filter)
