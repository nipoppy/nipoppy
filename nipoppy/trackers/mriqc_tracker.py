from pathlib import Path
import os

# Status flags
from nipoppy.trackers.tracker import (
    SUCCESS,
    FAIL
)

# relative to subject_dir
T1w_files_dict = {
    "html" : "../{}_{}_run-{}_T1w.html",
    "json" : "{}/anat/{}_{}_run-{}_T1w.json",
}
T2w_files_dict = {
    "html" : "../{}_{}_run-1_T2w.html",
    "json" : "{}/anat/{}_{}_run-{}_T2w.json",
}
func_files_dict = {
    "html" : "../{}_{}_task-rest_run-{}_bold.html",
    "json" : "{}/func/{}_{}_task-rest_run-{}_bold.json",
}

def check_staus(subject_dir, session_id, run_id, file_dict):
    participant_id = os.path.basename(subject_dir)
    filepath_status_list = []
    for k,v in file_dict.items():
        if k == "html":
            filepath = Path(f"{subject_dir}/" + v.format(participant_id, session_id, run_id))
        else:
            filepath = Path(f"{subject_dir}/" + v.format(session_id, participant_id, session_id, run_id))

        # print(f"filepath: {filepath}")
        filepath_status = Path.is_file(filepath)
        filepath_status_list.append(filepath_status)

    # print(f"filepath_status_list: {filepath_status_list}")
    if not any(filepath_status_list):
        status_msg = FAIL                    
    else:
        status_msg = SUCCESS

    return status_msg
        
def check_T1w(subject_dir, session_id, run_id):
    return check_staus(subject_dir, session_id, run_id, T1w_files_dict)
         
def check_T2w(subject_dir, session_id,run_id):
    return check_staus(subject_dir, session_id, run_id, T2w_files_dict)

def check_func(subject_dir, session_id, run_id):
    return check_staus(subject_dir, session_id, run_id, func_files_dict)



tracker_configs = {
    "pipeline_complete": check_T1w,
    
    "PHASE__": {
            "T2w": check_T2w,
            "func": check_func
            }
}