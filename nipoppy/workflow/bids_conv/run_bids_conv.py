#!/usr/bin/env python

import argparse
import json
import glob
import os
import shutil
import subprocess
from joblib import Parallel, delayed
from pathlib import Path
from typing import Iterable

import numpy as np
from bids.layout import parse_file_entities

import nipoppy.workflow.catalog as catalog
import nipoppy.workflow.logger as my_logger
from nipoppy.workflow.utils import (
    COL_CONV_STATUS,
    COL_DICOM_ID,
    DNAME_BACKUPS_STATUS,
    FNAME_STATUS, 
    load_status,
    save_backup,
    session_id_to_bids_session,
)

#Author: nikhil153
#Date: 07-Oct-2022
fname = __file__
CWD = os.path.dirname(os.path.abspath(fname))

def run_heudiconv(dicom_id, global_configs, session_id, stage, overlays, logger):
    logger.info(f"\n***Processing participant: {dicom_id}***")
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    SINGULARITY_PATH = global_configs["SINGULARITY_PATH"]
    CONTAINER_STORE = global_configs["CONTAINER_STORE"]
    HEUDICONV_CONTAINER = global_configs["BIDS"]["heudiconv"]["CONTAINER"]
    HEUDICONV_VERSION = global_configs["BIDS"]["heudiconv"]["VERSION"]
    HEUDICONV_CONTAINER = HEUDICONV_CONTAINER.format(HEUDICONV_VERSION)
    SINGULARITY_HEUDICONV = f"{CONTAINER_STORE}/{HEUDICONV_CONTAINER}"
    SINGULARITY_WD = "/scratch"
    SINGULARITY_DICOM_DIR = f"{SINGULARITY_WD}/dicom/ses-{session_id}"
    SINGULARITY_BIDS_DIR = f"{SINGULARITY_WD}/bids"
    HEURISTIC_FILE=f"{SINGULARITY_WD}/proc/heuristic.py"

    logger.info(f"Using SINGULARITY_HEUDICONV: {SINGULARITY_HEUDICONV}")

    flag_overlay = ''
    flag_bind = ''
    if overlays is not None:

        logger.info(f"Using overlay(s): {overlays}")
        for overlay in overlays:
            flag_overlay += f'--overlay {overlay} '

        for dname in ['bids', 'tabular', 'proc']:
            flag_bind += f'--bind {DATASET_ROOT}/{dname}:{SINGULARITY_WD}/{dname} '
    else:
        flag_bind = f'--bind {DATASET_ROOT}:{SINGULARITY_WD}'

    # Singularity CMD 
    SINGULARITY_CMD=f"{SINGULARITY_PATH} run {flag_overlay} {flag_bind} {SINGULARITY_HEUDICONV} "

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
        logger.error(f"Incorrect Heudiconv stage: {stage}")

    CMD_ARGS = SINGULARITY_CMD + Heudiconv_CMD 
    CMD = CMD_ARGS.split()

    logger.info(f"CMD:\n{CMD_ARGS}")
    heudiconv_proc_success = True
    try:
        subprocess.run(CMD, check=True) # raises CalledProcessError if non-zero return code
    except Exception as e:
        logger.error(f"bids run failed with exceptions: {e}")
        heudiconv_proc_success = False

    return heudiconv_proc_success

def run(global_configs, session_id, stage=2, overlays=None, n_jobs=2, dicom_id=None, logger=None, fpaths_to_copy=None):
    """ Runs the bids conv tasks 
    """
    session = session_id_to_bids_session(session_id)
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    log_dir = f"{DATASET_ROOT}/scratch/logs/"

    if fpaths_to_copy is None:
        fpaths_to_copy = []

    if logger is None:
        log_file = f"{log_dir}/bids_conv.log"
        logger = my_logger.get_logger(log_file)

    logger.info("-"*50)
    logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    logger.info(f"Running HeuDiConv stage: {stage}")
    logger.info(f"Number of parallel jobs: {n_jobs}")

    fpath_status = Path(DATASET_ROOT, 'scratch', 'raw_dicom', FNAME_STATUS)
    bids_dir = f"{DATASET_ROOT}/bids/"

    df_status = load_status(fpath_status)

    # participants to process with Heudiconv
    if dicom_id is None:
        heudiconv_df = catalog.get_new_dicoms(fpath_status, session_id, logger)
    else:
        # filter by DICOM ID if needed
        logger.info(f'Only running for participant: {dicom_id}')
        heudiconv_df = df_status.loc[df_status[COL_DICOM_ID] == dicom_id]
    
    heudiconv_participants = set(heudiconv_df["dicom_id"].values)
    n_heudiconv_participants = len(heudiconv_participants)

    if n_heudiconv_participants > 0:
        logger.info(f"\nStarting bids conversion for {n_heudiconv_participants} participant(s)")
    
        if stage == 2:
            logger.info(f"Copying ./heuristic.py to {DATASET_ROOT}/proc/heuristic.py (to be seen by Singularity container)")
            shutil.copyfile(f"{CWD}/heuristic.py", f"{DATASET_ROOT}/proc/heuristic.py")

            for fpath in fpaths_to_copy:
                fpath = Path(fpath)
                logger.info(f"Copying {fpath} to {DATASET_ROOT}/proc/{fpath.name} (to be seen by Singularity container)")
                shutil.copyfile(fpath, f"{DATASET_ROOT}/proc/{fpath.name}")

        if n_jobs > 1:
            ## Process in parallel! (Won't write to logs)
            heudiconv_results = Parallel(n_jobs=n_jobs)(delayed(run_heudiconv)(
                dicom_id, global_configs, session_id, stage, overlays, logger
                ) for dicom_id in heudiconv_participants)

        else:
            # Useful for debugging
            heudiconv_results = []
            for dicom_id in heudiconv_participants:
                res = run_heudiconv(dicom_id, global_configs, session_id, stage, overlays, logger) 
            heudiconv_results.append(res)

        # Check successful heudiconv runs
        n_heudiconv_success = np.sum(heudiconv_results)
        logger.info(f"Successfully ran Heudiconv (Stage 1 or Stage 2) for {n_heudiconv_success} out of {n_heudiconv_participants} participants")

        # Check succussful bids (NOTE: will count partial conversion as successful)
        participants_with_bids = {
            parse_file_entities(dpath)['subject']
            for dpath in
            glob.glob(f"{bids_dir}/sub-*/{session}")
        }

        new_participants_with_bids = heudiconv_participants & participants_with_bids
        
        logger.info("-"*50)

        if stage == 1:

            logger.info("Stage 1 done! Still need to run Stage 2")

        else:

            logger.info(f"Current successfully converted BIDS participants for session {session}: {len(participants_with_bids)}")
            logger.info(f"BIDS conversion completed for the {len(new_participants_with_bids)} out of {len(heudiconv_participants)} new participants")
            
            if len(new_participants_with_bids) > 0:
                heudiconv_df.loc[heudiconv_df[COL_DICOM_ID].isin(new_participants_with_bids), COL_CONV_STATUS] = True
                df_status.loc[heudiconv_df.index] = heudiconv_df
                save_backup(df_status, fpath_status, DNAME_BACKUPS_STATUS)

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

    parser.add_argument('--global_config', type=str, help='path to global configs for a given nipoppy dataset', required=True)
    parser.add_argument('--session_id', type=str, help='session id for the participant', required=True)
    parser.add_argument('--stage', type=int, default=2, help='heudiconv stage (either 1 or 2, default: 2)')
    parser.add_argument('--overlay', type=str, nargs='+', help='path(s) to Squashfs overlay(s)')
    parser.add_argument('--n_jobs', type=int, default=2, help='number of parallel processes (default: 2)')
    parser.add_argument('--dicom_id', type=str, help='dicom id for a single participant to run (default: run on all participants in the status file)')
    parser.add_argument('--copy_files', nargs='+', type=str, help='path(s) to file(s) to copy to /scratch/proc in the container')

    args = parser.parse_args()

    global_config_file = args.global_config
    session_id = args.session_id
    stage = args.stage
    overlays = args.overlay
    n_jobs = args.n_jobs
    dicom_id = args.dicom_id
    fpaths_to_copy = args.copy_files

    # Read global configs
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    # use absolute path
    if overlays is not None:
        if isinstance(overlays, str):
            overlays = [overlays]
        if not isinstance(overlays, Iterable):
            raise RuntimeError('overlays must be a string or iterable of strings')
        overlays = [Path(o).resolve() for o in overlays]

    run(global_configs, session_id, stage=stage, overlays=overlays, n_jobs=n_jobs, dicom_id=dicom_id, fpaths_to_copy=fpaths_to_copy)
