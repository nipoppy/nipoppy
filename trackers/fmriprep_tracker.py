from pathlib import Path
import os

# Status flags
SUCCESS="SUCCESS"
FAIL="FAIL"
INCOMPLETE="INCOMPLETE"
UNAVAILABLE="UNAVAILABLE"

# Globals
default_tpl_space = "MNI152NLin2009cSym" # Allowing res-1 or res-2 

# Sample output files
#sub-MNI0056D864854_ses-01_task-rest_run-1_space-T1w_desc-preproc_bold.nii.gz
#sub-MNI0056D864854_ses-01_task-rest_run-1_space-T1w_desc-brain_mask.json

fmriprep_anat_files_dict = {
    "brain_mask.json" : "desc-brain_mask.json",
    "brain_mask.nii" : "desc-brain_mask.nii.gz",
    "preproc_T1w.json": "desc-preproc_T1w.json",
    "preproc_T1w.nii": "desc-preproc_T1w.nii.gz",
    "dseg.nii": "dseg.nii.gz",
    "CSF_probseg": "label-CSF_probseg.nii.gz",
    "GM_probseg": "label-GM_probseg.nii.gz",
    "WM_probseg": "label-WM_probseg.nii.gz"
}
fmriprep_func_files_dict = {
    "brain_mask.json" : "desc-brain_mask.json",
    "brain_mask.nii" : "desc-brain_mask.nii.gz",
    "preproc_T1w.json": "desc-preproc_bold.json",
    "preproc_T1w.nii": "desc-preproc_bold.nii.gz",
}

fmriprep_modality_file_dict = {
                            "anat":fmriprep_anat_files_dict,
                            "func":fmriprep_func_files_dict
                            }


def check_anat_output(subject_dir, session_id, run_id):
    session = f"ses-{session_id}"
    participant_id = os.basename(subject_dir)
    status_msg = SUCCESS
    for k,v in fmriprep_anat_files_dict.items():
        if status_msg == SUCCESS:    
            default_tpl_status = []
            for file_suffix in [f"space-{default_tpl_space}-res_2_{v}",f"space-{default_tpl_space}-res_1_{v}"]:
                if run_id == None:
                    filepath = Path(f"{subject_dir}/{session}/anat/{participant_id}_{session}_{file_suffix}")
                else:
                    filepath = Path(f"{subject_dir}/{session}/anat/{participant_id}_{session}_{run_id}_{file_suffix}")
                
                filepath_status = Path.is_file(filepath)
                default_tpl_status.append(filepath_status)

            if not any(default_tpl_status):
                status_msg = FAIL                    
                break
        else:
            break

    return status_msg

def check_func_output(subject_dir, participant_id, ses_id, run_id, tpl_spaces, modality):
    """ Check output paths for function stream
    """
    status_msg = UNAVAILABLE

    # filepath = Path(f"{subject_dir}/{ses_id}/{modality}/{participant_id}_{ses_id}_task-{TASK}_{run_id}_{file_suffix}")

    return status_msg

def check_MNI152NLin2009cSym():
    """ Checks availability of MNI152NLin2009cSym space images
    """
    status_msg = UNAVAILABLE
    return status_msg
    
def check_MNI152NLin6Sym():
    """ Checks availability of MNI152NLin6Sym space images
    """
    status_msg = UNAVAILABLE
    return status_msg

def check_MNI152Lin():
    """ Checks availability of MNI152Lin space images
    """
    status_msg = UNAVAILABLE
    return status_msg

tracker_configs = {
    "pipeline_complete": check_anat_output,
    
    "Phase_": {
            "func": check_func_output
            },

    "Stage_": {
            "space-MNI152NLin2009cSym_res-1": check_MNI152NLin2009cSym,
            "space-MNI152NLin6Sym_res-1": check_MNI152NLin6Sym,
            "space-MNI152Lin_res-1": check_MNI152Lin
            }
}