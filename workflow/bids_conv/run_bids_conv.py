import argparse
import json
import subprocess
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import os
from joblib import Parallel, delayed
import glob
import workflow.logger as my_logger
import workflow.catalog as catalog

#Author: nikhil153
#Date: 07-Oct-2022
fname = __file__
CWD = os.path.dirname(os.path.abspath(fname))

def run_heudiconv(dicom_id, global_configs, session_id, stage, logger):
    logger.info(f"\n***Processing participant: {dicom_id}***")
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    DATASTORE_DIR = global_configs["DATASTORE_DIR"]
    SINGULARITY_PATH = global_configs["SINGULARITY_PATH"]
    CONTAINER_STORE = global_configs["CONTAINER_STORE"]
    HEUDICONV_CONTAINER = global_configs["BIDS"]["heudiconv"]["CONTAINER"]
    HEUDICONV_VERSION = global_configs["BIDS"]["heudiconv"]["VERSION"]
    HEUDICONV_CONTAINER = HEUDICONV_CONTAINER.format(HEUDICONV_VERSION)
    SINGULARITY_HEUDICONV = f"{CONTAINER_STORE}/{HEUDICONV_CONTAINER}"

    logger.info(f"Using SINGULARITY_HEUDICONV: {SINGULARITY_HEUDICONV}")

    SINGULARITY_WD = "/scratch"
    SINGULARITY_DICOM_DIR = f"{SINGULARITY_WD}/dicom/ses-{session_id}"
    SINGULARITY_BIDS_DIR = f"{SINGULARITY_WD}/bids"
    SINGULARITY_DATA_STORE="/data"
    HEURISTIC_FILE=f"{SINGULARITY_WD}/proc/heuristic.py"

    # Singularity CMD 
    SINGULARITY_CMD=f"{SINGULARITY_PATH} run -B {DATASET_ROOT}:{SINGULARITY_WD} \
        -B {DATASTORE_DIR}:{SINGULARITY_DATA_STORE} {SINGULARITY_HEUDICONV} "

    # Heudiconv CMD
    subject = "{subject}"
    if stage == 1:
        logger.info("Running stage 1")
        Heudiconv_CMD = f" -d {SINGULARITY_DICOM_DIR}/{subject}/* \
            -s {dicom_id} -c none \
            -f convertall \
            -o {SINGULARITY_BIDS_DIR} \
            --overwrite \
            -ss {session_id} "

    elif stage == 2:
        logger.info("Running stage 2")
        Heudiconv_CMD = f" -d {SINGULARITY_DICOM_DIR}/{subject}/* \
            -s {dicom_id} -c none \
            -f {HEURISTIC_FILE} \
            --grouping studyUID \
            -c dcm2niix -b --overwrite --minmeta \
            -o {SINGULARITY_BIDS_DIR} \
            -ss {session_id} "

    else:
        logger.error("Incorrect Heudiconv stage: {stage}")

    CMD_ARGS = SINGULARITY_CMD + Heudiconv_CMD 
    CMD = CMD_ARGS.split()

    logger.info(f"CMD:\n{CMD}")
    heudiconv_proc_success = True
    try:
        heudiconv_proc = subprocess.run(CMD)
    except Exception as e:
        logger.error(f"bids run failed with exceptions: {e}")
        heudiconv_proc_success = False

    return heudiconv_proc_success

def run(global_configs, session_id, logger=None, stage=2, n_jobs=2):
    """ Runs the bids conv tasks 
    """
    session = f"ses-{session_id}"
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    log_dir = f"{DATASET_ROOT}/scratch/logs/"

    if logger is None:
        log_file = f"{log_dir}/bids_conv.log"
        logger = my_logger.get_logger(log_file)

    logger.info("-"*50)
    logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    logger.info(f"Running HeuDiConv stage: {stage}")
    logger.info(f"Number of parallel jobs: {n_jobs}")

    mr_proc_manifest = f"{DATASET_ROOT}/tabular/mr_proc_manifest.csv"
    dicom_dir = f"{DATASET_ROOT}/dicom/{session}/"
    bids_dir = f"{DATASET_ROOT}/bids/"

    # participants to process with Heudiconv
    heudiconv_df = catalog.get_new_dicoms(mr_proc_manifest, dicom_dir, bids_dir, session_id, logger)
    heudiconv_participants = list(heudiconv_df["dicom_id"].values)
    n_heudiconv_participants = len(heudiconv_participants)

    if n_heudiconv_participants > 0:
        logger.info(f"\nStarting bids conversion for {n_heudiconv_participants} participant(s)")
    
        if stage == 2:
            logger.info(f"Copying ./heuristic.py to {DATASET_ROOT}/proc/heuristic.py (to be seen by Singularity container)")
            shutil.copyfile(f"{CWD}/heuristic.py", f"{DATASET_ROOT}/proc/heuristic.py")

        if n_jobs > 1:
            ## Process in parallel! (Won't write to logs)
            heudiconv_results = Parallel(n_jobs=n_jobs)(delayed(run_heudiconv)(
                dicom_id, global_configs, session_id, stage, logger
                ) for dicom_id in heudiconv_participants)

        else:
            # Useful for debugging
            heudiconv_results = []
            for dicom_id in heudiconv_participants:
                res = run_heudiconv(dicom_id, global_configs, session_id, stage, logger) 
                heudiconv_results.append(res)

        # Check successful heudiconv runs
        n_heudiconv_success = np.sum(heudiconv_results)
        logger.info(f"Successfully completed {n_heudiconv_success} out of {n_heudiconv_participants} heudiconv runs")
        
        # Check succussful bids (total sum: includes all previous runs)
        participant_bids_paths = glob.glob(f"{bids_dir}/sub-*")
        
        # Add newly processed bids_id to the manifest csv
        manifest_df = pd.read_csv(mr_proc_manifest)
    
        manifest_df.loc[(manifest_df["participant_id"].astype(str).isin(heudiconv_df["participant_id"]))
                         & (manifest_df["session"].astype(str) == session), 
                         "bids_id"] = heudiconv_df["bids_id"]

        manifest_df.to_csv(mr_proc_manifest, index=None)
        
        logger.info("-"*50)
        logger.info(f"Current successfully converted BIDS participants: {len(participant_bids_paths)}")
        
    else:
        logger.info(f"No new participants found for bids conversion...")

    logger.info("-"*50)
    logger.info("")

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to perform DICOM to BIDS conversion using HeuDiConv
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
    parser.add_argument('--session_id', type=str, help='session id for the participant')
    parser.add_argument('--stage', type=int, default=2, help='heudiconv stage (either 1 or 2)')
    parser.add_argument('--n_jobs', type=int, default=2, help='number of parallel processes')

    args = parser.parse_args()

    global_config_file = args.global_config
    session_id = args.session_id
    stage = args.stage
    n_jobs = args.n_jobs

    # Read global configs
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    run(global_configs, session_id, stage=stage, n_jobs=n_jobs)