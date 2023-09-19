from pathlib import Path
import os

# Status flags
from nipoppy.trackers.tracker import (
    SUCCESS,
    FAIL
)

from nipoppy.workflow.utils import participant_id_to_dicom_id

# File dicts per BIDS datatype
# "datatype":"suffix"
files_dict = {
    "anat": ["T1w"],
    "dwi": ["dwi"],
    "fmap": ["phasediff", "magnitude1", "magnitude2"],
    "func": ["bold"]
}

def check_staus(bids_layout, participant_id, session_id, run_id, datatype):
    # Remove non-alphanumeric characters from participant_id
    participant_id = participant_id_to_dicom_id(participant_id)
    suffix_list = files_dict[datatype]
    filepath_status_list = []
    for suffix in suffix_list: 
        scan_file = bids_layout.get(subject=participant_id, 
                                    session=session_id, 
                                    datatype=datatype, 
                                    run=run_id, 
                                    suffix=suffix, 
                                    extension='nii.gz')
        
        sidecar_file = bids_layout.get(subject=participant_id,
                                        session=session_id,
                                        datatype=datatype,
                                        run=run_id,
                                        suffix=suffix,
                                        extension='json')
        

        if (len(scan_file) > 0) & (len(sidecar_file) > 0):
            filepath_status = (Path.is_file(Path(scan_file[0].path))) & (Path.is_file(Path(sidecar_file[0].path)))
        else:
            filepath_status = False

        filepath_status_list.append(filepath_status)

    if not any(filepath_status_list):
        status_msg = FAIL                    
    else:
        status_msg = SUCCESS

    return status_msg
        
def check_T1w(bids_layout, participant_id, session_id, run_id):
    datatype = "anat"
    status = check_staus(bids_layout, participant_id, session_id, run_id, datatype)
    return status

def check_dwi(bids_layout, participant_id, session_id, run_id):
    datatype = "dwi"
    status = check_staus(bids_layout, participant_id, session_id, run_id, datatype)
    return status

def check_fmap(bids_layout, participant_id, session_id, run_id):
    datatype = "fmap"
    status = check_staus(bids_layout, participant_id, session_id, run_id, datatype)
    return status

def check_func(bids_layout, participant_id, session_id, run_id):
    datatype = "func"
    status = check_staus(bids_layout, participant_id, session_id, run_id, datatype)
    return status

def check_structural(bids_layout, participant_id, session_id, run_id):
    T1_status = check_T1w(bids_layout, participant_id, session_id, run_id)
    dwi_status = check_dwi(bids_layout, participant_id, session_id, run_id)
    if (T1_status == SUCCESS) & (dwi_status == SUCCESS):
        status = SUCCESS
    else:
        status = FAIL
        
    return status

tracker_configs = {
    "pipeline_complete": check_structural,
    
    "PHASE__": {
            "anat": check_T1w,
            "dwi": check_dwi,
            "fmap": check_fmap,
            "func": check_func
            }
}