#!/usr/bin/env python
import subprocess
import sys
import argparse
import json
import nipoppy.workflow.logger as my_logger
from pathlib import Path
import os

DNAME_BIDS_DB = 'bids_db_mriqc'
SINGULARITY_TEMPLATEFLOW_DIR = "/templateflow"
os.environ['SINGULARITYENV_TEMPLATEFLOW_HOME'] = SINGULARITY_TEMPLATEFLOW_DIR

def run(participant_id, global_configs, session_id, output_dir, modalities, logger=None, regenerate_bids_db=False):
    """ Runs mriqc command
    """
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    CONTAINER_STORE = global_configs["CONTAINER_STORE"]
    TEMPLATEFLOW_DIR = global_configs["TEMPLATEFLOW_DIR"]
    MRIQC_CONTAINER = global_configs["PROC_PIPELINES"]["mriqc"]["CONTAINER"]
    MRIQC_VERSION = global_configs["PROC_PIPELINES"]["mriqc"]["VERSION"]
    MRIQC_CONTAINER = MRIQC_CONTAINER.format(MRIQC_VERSION)
    SINGULARITY_CONTAINER = f"{CONTAINER_STORE}{MRIQC_CONTAINER}"

    bids_dir = f"{DATASET_ROOT}/bids/"
    proc_dir = f"{DATASET_ROOT}/proc/"

    # logging
    log_dir = f"{DATASET_ROOT}/scratch/logs/"
    if logger is None:
        log_file = f"{log_dir}/mriqc.log"
        logger = my_logger.get_logger(log_file)

    # path inside the container
    bids_db_dir = f"/mriqc_proc/{DNAME_BIDS_DB}"

    bids_db_dir_outside_container = f"{proc_dir}/{DNAME_BIDS_DB}"
    if not Path(bids_db_dir_outside_container).exists():
        logger.warning(f"Creating the BIDS database directory because it does not exist: {bids_db_dir_outside_container}")
        Path(bids_db_dir_outside_container).mkdir(parents=True, exist_ok=True)
    else:
        logger.info(f"Using existing BIDS database directory: {bids_db_dir_outside_container}")
       
    if regenerate_bids_db:
        for path in Path(bids_db_dir_outside_container).glob("*"):
            if path.is_file():
                logger.warning(f"Removing existing BIDS database file: {path}")
                path.unlink()
            else:
                logger.error(f"Expected to find only files in {bids_db_dir_outside_container} but found directory {path}")
                sys.exit(1)

    if output_dir is None:
        output_dir = f"{DATASET_ROOT}/derivatives"

    # create output dir
    mriqc_output_dir = f"{output_dir}/mriqc/{MRIQC_VERSION}/output/"
    Path(mriqc_output_dir).mkdir(parents=True, exist_ok=True)

    # create working dir (intermediate files)
    mriqc_work_dir = f"{output_dir}/mriqc/{MRIQC_VERSION}/work/"
    Path(mriqc_work_dir).mkdir(parents=True, exist_ok=True)

    logger.info("Starting mriqc run...")
    logger.info(f"participant: {participant_id}, session: {session_id}")
    logger.info(f"bids_dir: {bids_dir}")
    logger.info(f"output_dir: {output_dir}")
    logger.info(f"work_dir: {mriqc_work_dir}")

    # Singularity CMD 
    SINGULARITY_CMD=f"singularity run \
        -B {bids_dir}:{bids_dir}:ro \
        -B {proc_dir}:/mriqc_proc \
        -B {mriqc_output_dir}:/out \
        -B {mriqc_work_dir}:/work \
        -B {TEMPLATEFLOW_DIR}:{SINGULARITY_TEMPLATEFLOW_DIR} \
        --cleanenv \
        {SINGULARITY_CONTAINER} "

    # Compose mriqc command
    modalities_str = " ".join(modalities)
    MRIQC_CMD=f"{bids_dir} /out participant \
        --participant-label {participant_id} \
        --session-id {session_id} \
        --modalities {modalities_str} \
        --no-sub \
        --work-dir /work \
        --bids-database-dir {bids_db_dir}"
        # --bids-database-wipe" # wiping and regenerating bids db with catalog.py
    
    CMD_ARGS = SINGULARITY_CMD + MRIQC_CMD 
    CMD = CMD_ARGS.split()

    logger.info(f"Running mriqc container...")
    logger.info("-"*50)
    logger.info(f"CMD:\n{CMD}")
    logger.info("-"*50)
    
    try:
        mriqc_proc = subprocess.run(CMD)
        if mriqc_proc.returncode == 0:
            logger.info(f"Successfully completed mriqc run for participant: {participant_id}")
        else:
            logger.error(f"mriqc run failed with return code: {mriqc_proc.returncode}, for participant: {participant_id}")

    except Exception as e:
        logger.error(f"mriqc run failed with exceptions: {e}")


if __name__ == '__main__':

    # argparse
    HELPTEXT = """
    Script to run mriqc 
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--global_config', type=str, required=True, help='path to global configs for a given mr_proc dataset')
    parser.add_argument('--participant_id', type=str, required=True, help='participant id')
    parser.add_argument('--session_id', type=str, required=True, help='session id for the participant')
    parser.add_argument('--output_dir', type=str, default=None, help='specify custom output dir (if None, output is saved at <DATASET_ROOT>/derivatives/mriqc)')
    parser.add_argument('--modalities', nargs="*", required=True, help='specify modalities (i.e. suffixes) to QC. Possible options: T1w, T2w, bold, dwi')
    parser.add_argument('--regenerate_bids_db', action='store_true', help='regenerate PyBIDS database (default: use existing if available)')

    args = parser.parse_args()

    global_config_file = args.global_config
    participant_id = args.participant_id
    session_id = args.session_id
    output_dir = args.output_dir
    modalities = args.modalities
    regenerate_bids_db = args.regenerate_bids_db

    # Read global configs
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    output_dir = args.output_dir
    participant_id = args.participant_id
    session_id = args.session_id

    run(participant_id, global_configs, session_id, output_dir, modalities, regenerate_bids_db=regenerate_bids_db)
