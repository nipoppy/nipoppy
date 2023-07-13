from pathlib import Path
import os

# Status flags
SUCCESS="SUCCESS"
FAIL="FAIL"
INCOMPLETE="INCOMPLETE"
UNAVAILABLE="UNAVAILABLE"

# Sample output files
# sub-MNI0056D864854_ses-01_task-rest_run-1_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.json
# sub-MNI0056D864854_ses-01_task-rest_run-1_space-T1w_desc-preproc_bold.nii.gz
# sub-MNI0056D864854_ses-01_task-rest_run-1_space-T1w_desc-brain_mask.json
# sub-PD01134_ses-01_task-rest_run-1_space-MNI152NLin2009cSym_res-1_desc-brain_mask.json

# Globals (any one of this would qualify as success)
default_tpl_spaces = ["MNI152NLin2009cAsym","MNI152NLin2009cSym"]
default_tpl_resolutions = ["res-1","res-2"]

anat_files_dict = {
    "brain_mask.json" : "desc-brain_mask.json",
    "brain_mask.nii" : "desc-brain_mask.nii.gz",
    "preproc_T1w.json": "desc-preproc_T1w.json",
    "preproc_T1w.nii": "desc-preproc_T1w.nii.gz",
    "dseg.nii": "dseg.nii.gz",
    "CSF_probseg": "label-CSF_probseg.nii.gz",
    "GM_probseg": "label-GM_probseg.nii.gz",
    "WM_probseg": "label-WM_probseg.nii.gz"
}
func_files_dict = {
    "brain_mask.json" : "desc-brain_mask.json",
    "brain_mask.nii" : "desc-brain_mask.nii.gz",
    "preproc_bold.json": "desc-preproc_bold.json",
    "preproc_bold.nii": "desc-preproc_bold.nii.gz",
}

def check_output(subject_dir, file_check_dict, session_id, run_id, modality, 
                    tpl_spaces=default_tpl_spaces, tpl_resolutions=default_tpl_resolutions, task=None):
    session = f"ses-{session_id}"
    run = f"run-{run_id}"
    participant_id = os.path.basename(subject_dir)
    status_msg = SUCCESS
    for k,v in file_check_dict.items():
        if status_msg == SUCCESS:    
            default_tpl_status = []
            for tpl_space in tpl_spaces:
                for tpl_res in tpl_resolutions:
                    file_suffix = f"space-{tpl_space}_{tpl_res}_{v}"
                    if modality == "anat":
                        if run_id == None:
                            filepath = Path(f"{subject_dir}/{session}/{modality}/{participant_id}_{session}_{file_suffix}")
                        else:
                            filepath = Path(f"{subject_dir}/{session}/{modality}/{participant_id}_{session}_{run}_{file_suffix}")

                    elif modality == "func":
                        if run_id == None:
                            filepath = Path(f"{subject_dir}/{session}/{modality}/{participant_id}_{session}_{task}_{file_suffix}")
                        else:
                            filepath = Path(f"{subject_dir}/{session}/{modality}/{participant_id}_{session}_{task}_{run}_{file_suffix}")

                    else:
                        print(f"Unknown modality: {modality}")

                    filepath_status = Path.is_file(filepath)

                    default_tpl_status.append(filepath_status)

            if not any(default_tpl_status):
                status_msg = FAIL                    
                break
        else:
            break

    return status_msg

def check_anat_output(subject_dir, session_id, run_id):
    """ Check output paths for anat stream
    """
    modality = "anat"
    status_msg = check_output(subject_dir, anat_files_dict, session_id, run_id, modality)

    return status_msg

def check_func_output(subject_dir, session_id, run_id, task="task-rest"):
    """ Check output paths for func stream
    """
    modality = "func"
    status_msg = check_output(subject_dir, func_files_dict, session_id, run_id, modality, task=task)

    return status_msg

# TODO
def check_MNI152NLin2009cSym(subject_dir, session_id, run_id):
    """ Checks availability of MNI152NLin2009cSym space images
    """
    custom_tpl_spaces = ["MNI152NLin2009cSym"]
    custom_tpl_resolutions = ["res-1"]
    modality = "anat"
    file_dict = anat_files_dict
    status_msg = check_output(subject_dir, file_dict, session_id, run_id, modality,
                                tpl_spaces=custom_tpl_spaces, tpl_resolutions=custom_tpl_resolutions)
    return status_msg
    
def check_MNI152NLin2009cAsym(subject_dir, session_id, run_id):
    """ Checks availability of MNI152NLin2009cAsym space images
    """
    custom_tpl_spaces = ["MNI152NLin2009cAsym"]
    custom_tpl_resolutions = ["res-1"]
    modality = "anat"
    file_dict = anat_files_dict
    status_msg = check_output(subject_dir, file_dict, session_id, run_id, modality,
                                tpl_spaces=custom_tpl_spaces, tpl_resolutions=custom_tpl_resolutions)
    return status_msg

def check_MNI152NLin6Sym(subject_dir, session_id, run_id):
    """ Checks availability of MNI152NLin6Sym space images
    """
    custom_tpl_spaces = ["MNI152NLin6Sym"]
    custom_tpl_resolutions = ["res-1"]
    modality = "anat"
    file_dict = anat_files_dict
    status_msg = check_output(subject_dir, file_dict, session_id, run_id, modality,
                                tpl_spaces=custom_tpl_spaces, tpl_resolutions=custom_tpl_resolutions)
    return status_msg

def check_MNI152Lin(subject_dir, session_id, run_id):
    """ Checks availability of MNI152Lin space images
    """
    custom_tpl_spaces = ["MNI152Lin"]
    custom_tpl_resolutions = ["res-1"]
    modality = "anat"
    file_dict = anat_files_dict
    status_msg = check_output(subject_dir, file_dict, session_id, run_id, modality,
                                tpl_spaces=custom_tpl_spaces, tpl_resolutions=custom_tpl_resolutions)
    return status_msg   

tracker_configs = {
    "pipeline_complete": check_anat_output,
    
    "PHASE_": {
            "func": check_func_output
            },

    "STAGE_": {
            "space-MNI152NLin6Sym_res-1": check_MNI152NLin6Sym,
            "space-MNI152Lin_res-1": check_MNI152Lin
            }
}