from pathlib import Path
import os

# Status flags
from nipoppy.trackers.tracker import (
    SUCCESS,
    FAIL
)

## PPMI example: 
# json: <>/mriqc/23.1.0/output/sub-3000/ses-BL/anat/sub-3000_ses-BL_acq-sag3D_run-01_T1w.json
# html: <>/mriqc/23.1.0/output/sub-3000_ses-BL_acq-sag3D_run-01_T1w.html

## YLO example:
# json: <>/mriqc/23.1.0/output/sub-YLOPD169/ses-01/anat/sub-YLOPD169_ses-01_run-1_T1w.json
# html: <>/mriqc/23.1.0/output/sub-YLOPD169_ses-01_run-1_T1w.html

# relative to subject_dir
# need to do this separate for anat and func since suffix need not match the filepath inclusive of datatype
anat_files_dict = {
    "html" : "../{}.html",
    "json" : "{}/anat/{}.json",
}
func_files_dict = {
    "html" : "../{}.html",
    "json" : "{}/func/{}.json",
}

def check_status(subject_dir, session_id, run_id, acq_label, task_label, suffix, file_dict):

    # bids file-name tags in the correct order
    bids_id = os.path.basename(subject_dir)
    session = f"ses-{session_id}"
    task = f"task-{task_label}"
    acq = f"acq-{acq_label}"
    run = f"run-{run_id}"

    if suffix in ["T1w", "T2w"]:
        if (run_id == None) & (acq_label == None):
            fname = Path(f"{bids_id}_{session}_{suffix}")
        elif (run_id == None) & (acq_label != None):
            fname = Path(f"{bids_id}_{session}_{acq}_{suffix}")
        elif (run_id != None) & (acq_label == None):
            fname = Path(f"{bids_id}_{session}_{run}_{suffix}")
        else:
            fname = Path(f"{bids_id}_{session}_{acq}_{run}_{suffix}")

    elif suffix == "bold":
        if (run_id == None) & (acq_label == None):
            fname = Path(f"{bids_id}_{session}_{task}_{suffix}")
        elif (run_id == None) & (acq_label != None):
            fname = Path(f"{bids_id}_{session}_{task}_{acq}_{suffix}")
        elif (run_id != None) & (acq_label == None):
            fname = Path(f"{bids_id}_{session}_{task}_{run}_{suffix}")
        else:
            fname = Path(f"{bids_id}_{session}_{task}_{acq}_{run}_{suffix}")

    else:
        print(f"Unknown suffix: {suffix}")

    filepath_status_list = []
    for k,v in file_dict.items():
        if k == "html":
            filepath = Path(f"{subject_dir}/" + v.format(fname))
        else:
            filepath = Path(f"{subject_dir}/" + v.format(session, fname))

        # print(f"filepath: {filepath}")
        filepath_status = Path.is_file(filepath)
        filepath_status_list.append(filepath_status)

    # print(f"filepath_status_list: {filepath_status_list}")
    if not any(filepath_status_list):
        status_msg = FAIL                    
    else:
        status_msg = SUCCESS

    return status_msg
        
def check_T1w(subject_dir, session_id, run_id, acq_label=None, task_label=None):
    suffix = "T1w"
    return check_status(subject_dir, session_id, run_id, acq_label, task_label, suffix, anat_files_dict)
         
def check_T2w(subject_dir, session_id,run_id, acq_label=None, task_label=None):
    suffix = "T2w"
    return check_status(subject_dir, session_id, run_id, acq_label, task_label, suffix, anat_files_dict)

def check_func(subject_dir, session_id, run_id, acq_label=None, task_label="rest"):
    suffix = "bold"
    return check_status(subject_dir, session_id, run_id, acq_label, task_label, suffix, func_files_dict)

tracker_configs = {
    "pipeline_complete": check_T1w,
    
    "PHASE__": {
            "T2w": check_T2w,
            "func": check_func
            }
}