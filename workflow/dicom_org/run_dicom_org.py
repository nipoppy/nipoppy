#!/usr/bin/env python

import argparse
import json
import workflow.logger as my_logger
from joblib import Parallel, delayed
from pathlib import Path

import workflow.catalog as catalog
from workflow.dicom_org.utils import search_dicoms, copy_dicoms
from workflow.utils import (
    COL_ORG_STATUS, 
    DNAME_BACKUPS_STATUS, 
    load_status,
    participant_id_to_dicom_id, 
    save_backup,
    session_id_to_bids_session,
)

#Author: nikhil153
#Date: 07-Oct-2022


def reorg(participant, participant_dicom_dir, raw_dicom_dir, dicom_dir, invalid_dicom_dir, logger, use_symlinks, skip_dcm_check):
    """ Copy / Symlink raw dicoms into a flat participant dir
    """
    logger.info(f"\nparticipant_id: {participant}")

    participant_raw_dicom_dir = f"{raw_dicom_dir}/{participant_dicom_dir}/"

    raw_dcm_list, invalid_dicom_list = search_dicoms(participant_raw_dicom_dir, skip_dcm_check)
    logger.info(f"n_raw_dicom: {len(raw_dcm_list)}, n_skipped (invalid/derived): {len(invalid_dicom_list)}")

    # Remove non-alphanumeric chars (e.g. "_" from the participant_dir names)
    dicom_id = participant_id_to_dicom_id(participant)
    participant_dicom_dir = f"{dicom_dir}/{dicom_id}/"
    
    copy_dicoms(raw_dcm_list, participant_dicom_dir, use_symlinks)
    
    # Log skipped invalid dicom list for the participant
    invalid_dicoms_file = f"{invalid_dicom_dir}/{participant}_invalid_dicoms.json"
    invalid_dicom_dict = {participant: invalid_dicom_list}
    # Save skipped or invalid dicom file list
    with open(invalid_dicoms_file, "w") as outfile:
        json.dump(invalid_dicom_dict, outfile, indent=4)
        

def run(global_configs, session_id, logger=None, use_symlinks=True, skip_dcm_check=False, n_jobs=4):
    """ Runs the dicom reorg tasks 
    """
    session = session_id_to_bids_session(session_id)

    # populate relative paths
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    raw_dicom_dir = f"{DATASET_ROOT}/scratch/raw_dicom/{session}/"
    dicom_dir = f"{DATASET_ROOT}/dicom/{session}/"
    log_dir = f"{DATASET_ROOT}/scratch/logs/"
    invalid_dicom_dir = f"{log_dir}/invalid_dicom_dir/"

    fpath_status = f"{DATASET_ROOT}/scratch/raw_dicom/doughnut.csv"
    df_status = load_status(fpath_status)
    
    if logger is None:
        log_file = f"{log_dir}/dicom_org.log"
        logger = my_logger.get_logger(log_file)

    logger.info("-"*50)
    logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    logger.info(f"symlinks: {use_symlinks}")
    logger.info(f"session: {session}")
    logger.info(f"Number of parallel jobs: {n_jobs}")

    reorg_df = catalog.get_new_raw_dicoms(fpath_status, session_id, logger)
    n_dicom_reorg_participants = len(reorg_df)

    # start reorganizing
    if n_dicom_reorg_participants > 0:
        logger.info(f"\nStarting dicom reorg for {n_dicom_reorg_participants} participant(s)")
        # make session specific dicom subdir, if needed
        Path(dicom_dir).mkdir(parents=True, exist_ok=True)
        # make log dirs
        Path(f"{log_dir}").mkdir(parents=True, exist_ok=True)
        Path(invalid_dicom_dir).mkdir(parents=True, exist_ok=True)

        if n_jobs > 1:
            ## Process in parallel! (Won't write to logs)            
            Parallel(n_jobs=n_jobs)(delayed(reorg)(
                participant_id, dicom_id, raw_dicom_dir, dicom_dir, invalid_dicom_dir, logger, use_symlinks, skip_dcm_check
                ) 
                for participant_id, dicom_id in list(zip(reorg_df["participant_id"], reorg_df["participant_dicom_dir"]))
            )

        else: # Useful for debugging
            for participant_id, dicom_id in list(zip(reorg_df["participant_id"], reorg_df["participant_dicom_dir"])):
                reorg(participant_id, dicom_id, raw_dicom_dir, dicom_dir, invalid_dicom_dir, logger, use_symlinks, skip_dcm_check) 

        logger.info(f"\nDICOM reorg for {n_dicom_reorg_participants} participants completed")
        logger.info(f"Skipped (invalid/derived) DICOMs are listed here: {log_dir}")
        logger.info(f"DICOMs are now copied into {dicom_dir} and ready for bids conversion!")

        reorg_df[COL_ORG_STATUS] = True
        df_status.loc[reorg_df.index] = reorg_df
        save_backup(df_status, fpath_status, DNAME_BACKUPS_STATUS)

    else:
        logger.info(f"No new participants found for dicom reorg...")
        
    logger.info("-"*50)

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to reorganize raw (scanner dump) DICOMs into flattened dir structure needed for BIDS conversion using HeuDiConv
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global config file for your mr_proc dataset', required=True)
    parser.add_argument('--session_id', type=str, help='session (i.e. visit to process)', required=True)
    parser.add_argument('--no_symlinks', action='store_true', help='copy/duplicate files from raw_dicom to dicom (default: create symlinks)')
    parser.add_argument('--skip_dcm_check', action='store_true', help='skip raw dicoms checks to see if they are derived')
    parser.add_argument('--n_jobs', type=int, default=4, help='number of parallel processes')
    args = parser.parse_args()

    # read global configs
    global_config_file = args.global_config
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    session_id = args.session_id
    use_symlinks = not args.no_symlinks # Saves space and time! 
    skip_dcm_check = args.skip_dcm_check
    n_jobs = args.n_jobs

    run(global_configs, session_id, use_symlinks=use_symlinks, skip_dcm_check=skip_dcm_check, n_jobs=n_jobs)