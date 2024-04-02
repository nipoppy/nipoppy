import os
from pathlib import Path
import pandas as pd
from bids import BIDSLayout, BIDSLayoutIndexer
import shutil

from nipoppy.workflow.utils import (
    COL_CONV_STATUS,
    COL_PARTICIPANT_DICOM_DIR,
    COL_DOWNLOAD_STATUS,
    COL_ORG_STATUS, 
    COL_SESSION_MANIFEST,
    COL_SUBJECT_MANIFEST,
    COL_BIDS_ID_MANIFEST,
    load_doughnut,
)

from nipoppy.trackers.tracker import (
    SUCCESS,
    FAIL,
    UNAVAILABLE
)

def read_and_process_doughnut(fpath_doughnut, session_id, logger):
    # read current participant manifest 
    df_doughnut = load_doughnut(fpath_doughnut)
    session = f"ses-{session_id}"

    # filter session
    df_doughnut = df_doughnut.loc[df_doughnut[COL_SESSION_MANIFEST] == session]

    return df_doughnut

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


def get_new_downloads(fpath_doughnut, raw_dicom_dir, session_id, logger):
    """ Identify new dicoms not yet inside <DATASET_ROOT>/scratch/raw_dicom
    """
    df_doughnut = read_and_process_doughnut(fpath_doughnut, session_id, logger)
    participants = set(df_doughnut[COL_SUBJECT_MANIFEST])
    n_participants = len(participants)

    logger.info("-"*50)
    print("DEBUG DOWNLOAD")
    print(f"participants: {participants}")
    # check raw dicom dir    
    available_raw_dicom_dirs = list_dicoms(raw_dicom_dir, logger)
    print(f"available_raw_dicom_dirs: {available_raw_dicom_dirs}")
    logger.info("-"*50)
    
    n_available_raw_dicom_dirs = len(available_raw_dicom_dirs)
    available_raw_dicom_dirs_participant_ids = list(df_doughnut[df_doughnut[COL_PARTICIPANT_DICOM_DIR].isin(available_raw_dicom_dirs)][COL_SUBJECT_MANIFEST].astype(str).values)

    # check mismatch between doughnut file and raw_dicoms
    download_dicom_dir_participant_ids = set(participants) - set(available_raw_dicom_dirs_participant_ids)
    n_download_dicom_dirs = len(download_dicom_dir_participant_ids)

    download_df = df_doughnut[df_doughnut[COL_SUBJECT_MANIFEST].isin(download_dicom_dir_participant_ids)]

    logger.info("-"*50)
    logger.info(f"Identifying participants to be downloaded\n\n \
    - n_participants (listed in the doughnut file): {n_participants}\n \
    - n_available_raw_dicom_dirs: {n_available_raw_dicom_dirs}\n \
    - n_download_dicom_dirs: {n_download_dicom_dirs}\n")
    logger.info("-"*50)

    return download_df

def get_new_raw_dicoms(fpath_doughnut, session_id, logger):
    """ Identify new raw_dicoms not yet reorganized inside <DATASET_ROOT>/dicom
    """
    df_doughnut = read_and_process_doughnut(fpath_doughnut, session_id, logger)
    participants_all = set(df_doughnut[COL_SUBJECT_MANIFEST])
    n_participants_all = len(participants_all)

    # check raw dicom dir (downloaded)
    downloaded = set(df_doughnut.loc[df_doughnut[COL_DOWNLOAD_STATUS], COL_SUBJECT_MANIFEST])
    n_downloaded = len(downloaded)
    
    # check current dicom dir (already reorganized)
    downloaded_but_not_reorganized = downloaded & set(df_doughnut.loc[~df_doughnut[COL_ORG_STATUS], COL_SUBJECT_MANIFEST])
    n_downloaded_but_not_reorganized = len(downloaded_but_not_reorganized)

    reorg_df = df_doughnut.loc[df_doughnut[COL_SUBJECT_MANIFEST].isin(downloaded_but_not_reorganized)]

    # check participant dicom dirs
    if not reorg_df[COL_PARTICIPANT_DICOM_DIR].isna().all():
        logger.info("Using dicom filename from the doughnut file") 
    else:
        logger.warning(f"{COL_PARTICIPANT_DICOM_DIR} is not specified in the doughnut file")
        logger.info(f"Assuming {COL_SUBJECT_MANIFEST} is the dicom filename") 
        reorg_df[COL_PARTICIPANT_DICOM_DIR] = reorg_df[COL_SUBJECT_MANIFEST].copy()

    logger.info("-"*50)
    logger.info(
        f"Identifying participants to be reorganized\n\n"
        f"- n_participants_all (listed in the doughnut file): {n_participants_all}\n"
        f"- n_downloaded: {n_downloaded}\n"
        f"- n_missing: {n_participants_all - n_downloaded}\n"
        f"- n_downloaded_but_not_reorganized: {n_downloaded_but_not_reorganized}\n"
    )
    logger.info("-"*50)

    return reorg_df

def get_new_dicoms(fpath_doughnut, session_id, logger):
    """ Identify new dicoms not yet BIDSified
    """
    df_doughnut = read_and_process_doughnut(fpath_doughnut, session_id, logger)
    participants_all = set(df_doughnut[COL_SUBJECT_MANIFEST])
    n_participants_all = len(participants_all)

    # check current dicom dir (reorganized)
    organized = set(df_doughnut.loc[df_doughnut[COL_ORG_STATUS], COL_SUBJECT_MANIFEST])
    n_organized = len(organized)

    # check bids dir (already converted)
    organized_but_not_bids = organized & set(df_doughnut.loc[~df_doughnut[COL_CONV_STATUS], COL_SUBJECT_MANIFEST])
    n_organized_but_not_bids = len(organized_but_not_bids)

    heudiconv_df = df_doughnut.loc[df_doughnut[COL_SUBJECT_MANIFEST].isin(organized_but_not_bids)]

    logger.info("-"*50)
    logger.info(
        "Identifying participants to be BIDSified\n\n"
        f"- n_participants (listed in the doughnut file): {n_participants_all}\n"
        f"- n_organized: {n_organized}\n"
        f"- n_missing: {n_participants_all - n_organized}\n"
        f"- n_organized_but_not_bids: {n_organized_but_not_bids}\n"
    )
    logger.info("-"*50)

    return heudiconv_df

def get_new_proc_participants(global_configs, session_id, pipeline, logger):
    """ Eat doughnuts (expected) and bagels (on-disk) to identify new participants
    """
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    pipeline_version = global_configs["PROC_PIPELINES"][pipeline]["VERSION"]

    session = f"ses-{session_id}"

    logger.info(f"Identifying new proc participants for session: {session} and pipeline: {pipeline}")

    # Grab BIDS participants from the doughnut
    doughnut_file = f"{DATASET_ROOT}/scratch/raw_dicom/doughnut.csv"
    doughnut_df = pd.read_csv(doughnut_file)
    doughnut_df[COL_CONV_STATUS] = doughnut_df[COL_CONV_STATUS].astype(bool)
    bids_participants = doughnut_df[(doughnut_df[COL_SESSION_MANIFEST]==session) & (doughnut_df[COL_CONV_STATUS])][COL_BIDS_ID_MANIFEST].unique()
    n_bids_participants = len(bids_participants)

    logger.info(f"n_bids_participants: {n_bids_participants}, session_id: {session_id}")

    # Grab processed participants from the bagel
    bagel_file = f"{DATASET_ROOT}/derivatives/bagel.csv"
    bagel_df = pd.read_csv(bagel_file)
    bagel_df = bagel_df[bagel_df[COL_SESSION_MANIFEST] == session]
    bagel_df = bagel_df[(bagel_df["pipeline_name"] == pipeline) & (bagel_df["pipeline_version"] == pipeline_version)]
    on_disk_participants = bagel_df[bagel_df["pipeline_complete"]==SUCCESS][COL_BIDS_ID_MANIFEST].unique()
    n_on_disk_participants = len(on_disk_participants)

    logger.info(f"n_on_disk_participants: {n_on_disk_participants}")

    # Identify new participants
    new_proc_participants = list(set(bids_participants) - set(on_disk_participants))
    n_new_proc_participants = len(new_proc_participants)
    logger.info(f"n_new_proc_participants: {n_new_proc_participants}")

    return new_proc_participants, on_disk_participants

# NOTE - currently not using it because of pybids warning on "absolute_paths=False"
def generate_pybids_index(global_configs, session_id, pipeline, ignore_patterns, logger, run_id=1, bids_db_path=None):
    """ Generates a pybids index for a selected list of bids_ids using --ignore argument. 
        You can pass a list of folder names, or a regex pattern to the ignore argument.
    """
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    bids_dir = f"{DATASET_ROOT}/bids"

    if bids_db_path == None:
        bids_db_path = f"{DATASET_ROOT}/proc/bids_db_{pipeline}"
    
    # Get list of on-disk and new participants
    # We will completely ignore the on-disk participants in the BIDS index
    # We will ignore certain modalities / acq patterns for the new participants (avoid mriqc and fmriprep errors)
    # Example ignore patterns: ["/anat/{}_{}_{}_NM"]

    new_proc_participants, on_disk_participants = get_new_proc_participants(global_configs, session_id, pipeline, logger)

    n_on_disk_participants = len(on_disk_participants)
    logger.info(f"ignoring ({n_on_disk_participants}) n_on_disk_participants from pybids index")

    # Completely ignore these subjects
    ignore_subjects = on_disk_participants
    ignore_session = f"ses-{session_id}"
    ignore_run = f"run-{run_id}"
    # Need to have "ses-" appended to the subject_id to avoid wildcard matching
    ignore_pattern_list = list(pd.Series(ignore_subjects) + f"/{ignore_session}")

    # Ignore specific sessions and datatypes / acq patterns for these subjects
    index_subjects = new_proc_participants
    ignore_SRE_patterns = ignore_patterns

    for sub in index_subjects:
        for sre_pattern in ignore_SRE_patterns:
            sre_pattern = sre_pattern.format(sub, ignore_session, ignore_run)
            ignore_pattern = f"{sub}/{ignore_session}{sre_pattern}"
            ignore_pattern_list.append(ignore_pattern)

    logger.info(f"ignoring {len(ignore_pattern_list)} subjects + datatype + acq patterns from pybids index")

    # Check if old db exists
    if Path.is_dir(Path(bids_db_path)):
        shutil.rmtree(bids_db_path)
        logger.info(f"removed old pybids index at: {bids_db_path}")

    # TODO
    # Check diff against previous index and only update if there are new participants

    indexer = BIDSLayoutIndexer(ignore=ignore_pattern_list)
    layout = BIDSLayout(bids_dir, indexer=indexer) # Throws deprecation warning
    
    indexed_subjects = layout.get(return_type='id', target='subject', suffix='T1w')
    n_indexed_subjects = len(indexed_subjects)
    logger.debug(f"number of indexed subjects: {n_indexed_subjects}")

    logger.info(f"new pybids index generated at: {bids_db_path}")
    layout.save(bids_db_path)

    return bids_db_path