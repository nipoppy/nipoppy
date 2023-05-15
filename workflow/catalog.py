import pandas as pd
import os
from pathlib import Path

from workflow.utils import (
    COL_DOWNLOAD_STATUS, 
    COL_ORG_STATUS, 
    participant_id_to_dicom_id, 
    dicom_id_to_bids_id,
)

# Globals
# status file columns
PARTICIPANT_ID = "participant_id"
PARTICIPANT_DICOM_DIR = "participant_dicom_dir"
VISIT = "visit"
SESSION = "session"
DICOM_ID = "dicom_id"
BIDS_ID  = "bids_id"

def read_status(fpath_status):
    return pd.read_csv(fpath_status, dtype={col: str for col in [PARTICIPANT_ID, PARTICIPANT_DICOM_DIR, VISIT, SESSION, DICOM_ID, BIDS_ID]})

def read_and_process_status(status_csv, session_id, logger):
    # read current participant manifest 
    status_df = read_status(status_csv)
    session = f"ses-{session_id}"

    # filter session
    status_df = status_df[status_df[SESSION] == session]
    status_df[PARTICIPANT_ID] = status_df[PARTICIPANT_ID].astype(str)
    participants = status_df[PARTICIPANT_ID].str.strip().values

    # generate dicom_id
    status_df[DICOM_ID] = [participant_id_to_dicom_id(idx) for idx in participants]

    # generate bids_id
    status_df[BIDS_ID] = [dicom_id_to_bids_id(dicom_id) for dicom_id in status_df[DICOM_ID]]

    # check participant dicom dirs
    if not status_df[PARTICIPANT_DICOM_DIR].isna().all():
        logger.info("Using dicom filename from the status file") 
    else:
        logger.warning(f"{PARTICIPANT_DICOM_DIR} is not specified in the status file")
        logger.info("Assuming dicom_id is the dicom filename") 
        status_df[PARTICIPANT_DICOM_DIR] = status_df[DICOM_ID].copy()

    return status_df

def list_dicoms(dcm_dir, logger):
    # check current dicom dir
    if Path.is_dir(Path(dcm_dir)):
        participant_dcm_dirs = next(os.walk(dcm_dir))[1]
    else:
        participant_dcm_dirs = []
        logger.warning(f"No participant dicoms found in {dcm_dir}")

    return participant_dcm_dirs

def list_bids(bids_dir, session_id, logger):
    # available participant bids dirs (for particular session)
    if Path.is_dir(Path(bids_dir)):
        current_bids_dirs = next(os.walk(bids_dir))[1]
        current_bids_session_dirs = []
        for pbd in current_bids_dirs:
            ses_dir_path = Path(f"{bids_dir}/{pbd}/ses-{session_id}")
            if Path.is_dir(ses_dir_path):
                current_bids_session_dirs.append(pbd)
    else:
        current_bids_session_dirs = []
        logger.warning(f"No participant bids dir found in {bids_dir}")

    return current_bids_session_dirs


def get_new_downloads(status_csv, raw_dicom_dir, session_id, logger):
    """ Identify new dicoms not yet inside <DATASET_ROOT>/scratch/raw_dicom
    """
    status_df = read_and_process_status(status_csv, session_id, logger)
    participants = set(status_df[PARTICIPANT_ID])
    n_participants = len(participants)

    logger.info("-"*50)
    print("DEBUG DOWNLOAD")
    print(f"participants: {participants}")
    # check raw dicom dir    
    available_raw_dicom_dirs = list_dicoms(raw_dicom_dir, logger)
    print(f"available_raw_dicom_dirs: {available_raw_dicom_dirs}")
    logger.info("-"*50)
    
    n_available_raw_dicom_dirs = len(available_raw_dicom_dirs)
    available_raw_dicom_dirs_participant_ids = list(status_df[status_df[PARTICIPANT_DICOM_DIR].isin(available_raw_dicom_dirs)][PARTICIPANT_ID].astype(str).values)

    # check mismatch between status file and raw_dicoms
    download_dicom_dir_participant_ids = set(participants) - set(available_raw_dicom_dirs_participant_ids)
    n_download_dicom_dirs = len(download_dicom_dir_participant_ids)

    download_df = status_df[status_df[PARTICIPANT_ID].isin(download_dicom_dir_participant_ids)]

    logger.info("-"*50)
    logger.info(f"Identifying participants to be downloaded\n\n \
    - n_participants (listed in the status file): {n_participants}\n \
    - n_available_raw_dicom_dirs: {n_available_raw_dicom_dirs}\n \
    - n_download_dicom_dirs: {n_download_dicom_dirs}\n")
    logger.info("-"*50)

    return download_df

def get_new_raw_dicoms(status_csv, session_id, logger):
    """ Identify new raw_dicoms not yet reorganized inside <DATASET_ROOT>/dicom
    """
    status_df = read_and_process_status(status_csv, session_id, logger)
    participants_all = set(status_df[PARTICIPANT_ID])
    n_participants_all = len(participants_all)

    # check raw dicom dir (downloaded)
    downloaded = set(status_df.loc[status_df[COL_DOWNLOAD_STATUS], PARTICIPANT_ID])
    n_downloaded = len(downloaded)
    
    # check current dicom dir (already reorganized)
    downloaded_but_not_reorganized = downloaded & set(status_df.loc[~status_df[COL_ORG_STATUS], PARTICIPANT_ID])
    n_downloaded_but_not_reorganized = len(downloaded_but_not_reorganized)

    reorg_df = status_df[status_df[PARTICIPANT_ID].isin(downloaded_but_not_reorganized)]

    logger.info("-"*50)
    logger.info(
        f"Identifying participants to be reorganized\n\n"
        f"- n_participants_all (listed in the status file): {n_participants_all}\n"
        f"- n_downloaded: {n_downloaded}\n"
        f"- n_missing: {n_participants_all - n_downloaded}\n"
        f"- n_downloaded_but_not_reorganized: {n_downloaded_but_not_reorganized}\n"
    )
    logger.info("-"*50)

    return reorg_df

def get_new_dicoms(status_csv, dicom_dir, bids_dir, session_id, logger):
    """ Identify new dicoms not yet BIDSified
    """
    status_df = read_and_process_status(status_csv, session_id, logger)
    participants = set(status_df[PARTICIPANT_ID])
    n_participants = len(participants)
    dicom_ids = set(status_df[DICOM_ID])
    bids_ids = set(status_df[BIDS_ID])

    # check current bids dir
    current_bids_dirs = list_bids(bids_dir, session_id, logger)
    current_bids_dirs = bids_ids & set(current_bids_dirs)
    n_current_bids_dirs = len(current_bids_dirs)

    # check current dicom dir
    available_dicom_dirs = list_dicoms(dicom_dir, logger)
    n_available_dicom_dirs = len(available_dicom_dirs)

    # check mismatch between status file and participant dicoms
    missing_dicom_dirs = set(dicom_ids) - set(available_dicom_dirs)
    n_missing_dicom_dirs = len(missing_dicom_dirs)

    current_bids_dirs_dicom_ids = status_df[status_df[BIDS_ID].isin(current_bids_dirs)][DICOM_ID]

    # participants to process with Heudiconv
    heudiconv_participants = set(dicom_ids) - set(missing_dicom_dirs) - set(current_bids_dirs_dicom_ids)
    n_heudiconv_participants = len(heudiconv_participants)
    heudiconv_df = status_df[status_df[DICOM_ID].isin(heudiconv_participants)]

    logger.info("-"*50)
    logger.info(f"Identifying participants to be BIDSified\n\n \
    - n_particitpants (listed in the status file): {n_participants}\n \
    - n_current_bids_dirs (current): {n_current_bids_dirs}\n \
    - n_available_dicom_dirs (available): {n_available_dicom_dirs}\n \
    - n_missing_dicom_dirs: {n_missing_dicom_dirs}\n \
    - heudiconv participants to processes: {n_heudiconv_participants}\n")
    logger.info("-"*50)

    return heudiconv_df