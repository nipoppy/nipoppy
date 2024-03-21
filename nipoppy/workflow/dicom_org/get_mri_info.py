import pandas as pd
import os 
import argparse
import json
from pydicom import dcmread
from pathlib import Path
import nipoppy.workflow.logger as my_logger
from nipoppy.workflow.dicom_org.utils import check_valid_dicom
from nipoppy.workflow.utils import (
    COL_ORG_STATUS,
    DNAME_BACKUPS_DOUGHNUT,
    FNAME_DOUGHNUT,
    load_doughnut,
    participant_id_to_dicom_id,
    save_backup,
    session_id_to_bids_session,
)

def get_acq_date(dcm_dir):
    """ Parses dicom header to get the acquisition date
    """
    dcm_file = os.listdir(dcm_dir)[0]
    dcm_path = os.path.join(dcm_dir, dcm_file)

    if check_valid_dicom(dcm_path):
        with open(dcm_path, 'rb') as infile:
            ds = dcmread(infile)

        acq_date = ds.AcquisitionDate
        acq_date = pd.to_datetime(acq_date, format="%Y%m%d")

    else:
        acq_date = None

    return acq_date

def run(global_configs, output_file):
    """ Run get_acq_date for all participants
    """
    session = session_id_to_bids_session(session_id)

    # populate relative paths
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    raw_dicom_dir = f"{DATASET_ROOT}/scratch/raw_dicom/{session}/"
    log_dir = f"{DATASET_ROOT}/scratch/logs/"

    fpath_doughnut = f"{DATASET_ROOT}/scratch/raw_dicom/{FNAME_DOUGHNUT}"
    fpath_MRI_acqdata = f"{DATASET_ROOT}/scratch/raw_dicom/{output_file}"

    df_doughnut = load_doughnut(fpath_doughnut)
    
    if logger is None:
        log_file = f"{log_dir}/mri_metadata.log"
        logger = my_logger.get_logger(log_file)

    logger.info("-"*50)
    logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    logger.info(f"session: {session}")

    n_doughnut_participants = df_doughnut["participant_dicom_dir"].nunique()
    n_doughnut_sessions = df_doughnut["session_id"].nunique()   

    logger.info(f"n_doughnut_participants: {n_doughnut_participants}")
    logger.info(f"n_doughnut_sessions: {n_doughnut_sessions}")

    if n_doughnut_participants > 0:
        logger.info(f"Processing {n_doughnut_participants} participants")
        
        for idx, row in df_doughnut.iterrows():
            participant_dicom_dir = row["participant_dicom_dir"]
            session_id = row["session_id"]
            dicom_path = f"{raw_dicom_dir}/{session_id}/{participant_dicom_dir}/"
            acq_date = get_acq_date(f"{dicom_path}")
            df_doughnut.loc[idx, "scanner_acq_date"] = acq_date

        df_doughnut.to_csv(fpath_MRI_acqdata, index=False)
        logger.info(f"Saved MRI acquisition data to: {fpath_MRI_acqdata}")

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to get the acquisition date for all MRI scans in a session
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global config file for your nipoppy dataset', required=True)
    parser.add_argument('--output_file', type=str, help='output file name', default="MRI_acqdata.csv") #TODO merge this with doughtnut
    args = parser.parse_args()

    # read global configs
    global_config_file = args.global_config
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)

    output_file = args.output_file

    run(global_configs, output_file)