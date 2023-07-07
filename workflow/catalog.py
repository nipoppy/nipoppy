import pandas as pd
import os
from pathlib import Path

from workflow.utils import (
    COL_BIDS_ID_MANIFEST,
    COL_CONV_STATUS,
    COL_PARTICIPANT_DICOM_DIR,
    COL_DICOM_ID,
    COL_DOWNLOAD_STATUS,
    COL_ORG_STATUS, 
    COL_SESSION_MANIFEST,
    COL_SUBJECT_MANIFEST,
    COL_VISIT_MANIFEST,
    load_status,
)

def read_and_process_status(status_csv, session_id, logger):
    # read current participant manifest 
    status_df = load_status(status_csv)
    session = f"ses-{session_id}"

    # filter session
    status_df = status_df[status_df[COL_SESSION_MANIFEST] == session]
    status_df[COL_SUBJECT_MANIFEST] = status_df[COL_SUBJECT_MANIFEST].astype(str)

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
    participants = set(status_df[COL_SUBJECT_MANIFEST])
    n_participants = len(participants)

    logger.info("-"*50)
    print("DEBUG DOWNLOAD")
    print(f"participants: {participants}")
    # check raw dicom dir    
    available_raw_dicom_dirs = list_dicoms(raw_dicom_dir, logger)
    print(f"available_raw_dicom_dirs: {available_raw_dicom_dirs}")
    logger.info("-"*50)
    
    n_available_raw_dicom_dirs = len(available_raw_dicom_dirs)
    available_raw_dicom_dirs_participant_ids = list(status_df[status_df[COL_PARTICIPANT_DICOM_DIR].isin(available_raw_dicom_dirs)][COL_SUBJECT_MANIFEST].astype(str).values)

    # check mismatch between status file and raw_dicoms
    download_dicom_dir_participant_ids = set(participants) - set(available_raw_dicom_dirs_participant_ids)
    n_download_dicom_dirs = len(download_dicom_dir_participant_ids)

    download_df = status_df[status_df[COL_SUBJECT_MANIFEST].isin(download_dicom_dir_participant_ids)]

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
    participants_all = set(status_df[COL_SUBJECT_MANIFEST])
    n_participants_all = len(participants_all)

    # check raw dicom dir (downloaded)
    downloaded = set(status_df.loc[status_df[COL_DOWNLOAD_STATUS], COL_SUBJECT_MANIFEST])
    n_downloaded = len(downloaded)
    
    # check current dicom dir (already reorganized)
    downloaded_but_not_reorganized = downloaded & set(status_df.loc[~status_df[COL_ORG_STATUS], COL_SUBJECT_MANIFEST])
    n_downloaded_but_not_reorganized = len(downloaded_but_not_reorganized)

    reorg_df = status_df.loc[status_df[COL_SUBJECT_MANIFEST].isin(downloaded_but_not_reorganized)]

    # check participant dicom dirs
    if not reorg_df[COL_PARTICIPANT_DICOM_DIR].isna().all():
        logger.info("Using dicom filename from the status file") 
    else:
        logger.warning(f"{COL_PARTICIPANT_DICOM_DIR} is not specified in the status file")
        logger.info("Assuming dicom_id is the dicom filename") 
        reorg_df[COL_PARTICIPANT_DICOM_DIR] = reorg_df[COL_DICOM_ID].copy()

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

def get_new_dicoms(status_csv, session_id, logger):
    """ Identify new dicoms not yet BIDSified
    """
    status_df = read_and_process_status(status_csv, session_id, logger)
    participants_all = set(status_df[COL_SUBJECT_MANIFEST])
    n_participants_all = len(participants_all)

    # check current dicom dir (reorganized)
    organized = set(status_df.loc[status_df[COL_ORG_STATUS], COL_SUBJECT_MANIFEST])
    n_organized = len(organized)

    # check bids dir (already converted)
    organized_but_not_bids = organized & set(status_df.loc[~status_df[COL_CONV_STATUS], COL_SUBJECT_MANIFEST])
    n_organized_but_not_bids = len(organized_but_not_bids)

    heudiconv_df = status_df.loc[status_df[COL_SUBJECT_MANIFEST].isin(organized_but_not_bids)]

    logger.info("-"*50)
    logger.info(
        "Identifying participants to be BIDSified\n\n"
        f"- n_participants (listed in the status file): {n_participants_all}\n"
        f"- n_organized: {n_organized}\n"
        f"- n_missing: {n_participants_all - n_organized}\n"
        f"- n_organized_but_not_bids: {n_organized_but_not_bids}\n"
    )
    logger.info("-"*50)

    return heudiconv_df