
BIDS_SUBJECT_PREFIX = 'sub-'
BIDS_SESSION_PREFIX = 'ses-'

def participant_id_to_dicom_id(participant_id):
    # keep only alphanumeric characters
    participant_id = str(participant_id)
    dicom_id = ''.join(filter(str.isalnum, participant_id))
    return dicom_id

def dicom_id_to_bids_id(dicom_id):
    return subject_to_bids(dicom_id)

def subject_to_bids(subject_id):
    # add BIDS prefix if it doesn't already exist
    subject_id = str(subject_id)
    if subject_id.startswith(BIDS_SUBJECT_PREFIX):
        return subject_id
    else:
        return f'{BIDS_SUBJECT_PREFIX}{subject_id}'

def participant_id_to_bids_id(participant_id):
    return dicom_id_to_bids_id(participant_id_to_dicom_id(participant_id))

def session_to_bids(session_id):
    # add BIDS prefix if it doesn't already exist
    session_id = str(session_id)
    if session_id.startswith(BIDS_SESSION_PREFIX):
        return session_id
    else:
        return f'{BIDS_SESSION_PREFIX}{session_id}'
