import datetime
import os
from pathlib import Path

import pandas as pd

# BIDS format
BIDS_SUBJECT_PREFIX = 'sub-'
BIDS_SESSION_PREFIX = 'ses-'

# directory/file names
DNAME_BACKUPS_MANIFEST = '.manifests'
DNAME_BACKUPS_DOUGHNUT = '.doughnuts'
DNAME_BACKUPS_BAGEL = '.bagels'
FNAME_MANIFEST = 'manifest.csv'
FNAME_DOUGHNUT = 'doughnut.csv'
FNAME_BAGEL = 'bagel.csv'

# for creating backups
TIMESTAMP_FORMAT = '%Y%m%d_%H%M'
EXT_SYMBOL = '.'
SEP_FNAME_BACKUP = '-'

# manifest file columns
COL_SUBJECT_MANIFEST = 'participant_id'
COL_BIDS_ID_MANIFEST = 'bids_id'
COL_VISIT_MANIFEST = 'visit'
COL_SESSION_MANIFEST = 'session'
COL_DATATYPE_MANIFEST = 'datatype'
COLS_MANIFEST = [COL_SUBJECT_MANIFEST, COL_VISIT_MANIFEST, 
                 COL_SESSION_MANIFEST, COL_DATATYPE_MANIFEST]

# status file columns
COL_PARTICIPANT_DICOM_DIR = 'participant_dicom_dir'
COL_DICOM_ID = 'dicom_id'
COL_DOWNLOAD_STATUS = 'downloaded'
COL_ORG_STATUS = 'organized'
COL_CONV_STATUS = 'converted'
COLS_STATUS = [COL_SUBJECT_MANIFEST, COL_SESSION_MANIFEST, 
               COL_PARTICIPANT_DICOM_DIR, COL_DICOM_ID, COL_BIDS_ID_MANIFEST, 
               COL_DOWNLOAD_STATUS, COL_ORG_STATUS, COL_CONV_STATUS]

def participant_id_to_dicom_id(participant_id):
    # keep only alphanumeric characters
    participant_id = str(participant_id)
    dicom_id = ''.join(filter(str.isalnum, participant_id))
    return dicom_id

def dicom_id_to_bids_id(dicom_id):
    return f'{BIDS_SUBJECT_PREFIX}{dicom_id}'

def participant_id_to_bids_id(participant_id):
    return dicom_id_to_bids_id(participant_id_to_dicom_id(participant_id))

def session_id_to_bids_session(session_id):
    # add BIDS prefix if it doesn't already exist
    session_id = str(session_id)
    if session_id.startswith(BIDS_SESSION_PREFIX):
        return session_id
    else:
        return f'{BIDS_SESSION_PREFIX}{session_id}'

def save_backup(df: pd.DataFrame, fpath_symlink, dname: str, use_relative_path=True):
    
    fpath_symlink = Path(fpath_symlink)

    timestamp = datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
    fpath_symlink_components = fpath_symlink.name.split(EXT_SYMBOL)
    fname_backup = EXT_SYMBOL.join([f'{fpath_symlink_components[0]}{SEP_FNAME_BACKUP}{timestamp}'] + fpath_symlink_components[1:])
    fpath_backup: Path = fpath_symlink.parent / dname / fname_backup

    fpath_backup.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fpath_backup, index=False, header=True)
    os.chmod(fpath_backup, 0o664)
    print(f'\nFile written to: {fpath_backup}')

    if use_relative_path:
        fpath_backup = os.path.relpath(fpath_backup, fpath_symlink.parent)

    if fpath_symlink.exists():
        fpath_symlink.unlink()
    fpath_symlink.symlink_to(fpath_backup)
    print(f'Created symlink: {fpath_symlink} -> {fpath_backup}')

def load_manifest(fpath_manifest):

    return pd.read_csv(
        fpath_manifest, 
        dtype={
            col: str 
            for col 
            in [COL_SUBJECT_MANIFEST, COL_SESSION_MANIFEST]
        },
        converters={COL_DATATYPE_MANIFEST: pd.eval}
    )

def load_doughnut(fpath_doughnut):
    return pd.read_csv(
        fpath_doughnut, 
        dtype={
            col: str 
            for col in [
                COL_SUBJECT_MANIFEST, 
                COL_PARTICIPANT_DICOM_DIR, 
                COL_VISIT_MANIFEST, 
                COL_SESSION_MANIFEST, 
                COL_DICOM_ID, 
                COL_BIDS_ID_MANIFEST,
            ]
        },
    )
