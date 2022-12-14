from re import ASCII
import pandas as pd
from pathlib import Path
import argparse
import glob
import os

HELPTEXT = """
Script to validate fmriprep output
"""
#Author: nikhil153
#Date: 27-July-2022

# globals
MODALITIES = ["anat","func"]
TASK = "rest"

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

fsl_files_dict = { 
    "FSL_FLIRT": "desc-PMF6_T1w.nii.gz",
    # "FSL_FNIRT": "desc-FNIRT_T1w.nii.gz" (Need to be copied from Beluga SquashFS)
}

# argparse
parser = argparse.ArgumentParser(description=HELPTEXT)

# data
parser.add_argument('--fmriprep_dir', dest='fmriprep_dir',                      
                    help='path to fmriprep_dir with all the subjects')

parser.add_argument('--ses', dest='ses',                      
                    help='session id e.g. bl')

parser.add_argument('--run', dest='run', default=None,                  
                    help='run id e.g. 1')

parser.add_argument('--tpl_spaces', dest='tpl_spaces', nargs='*', default=["MNI152NLin2009cAsym_res-2"], 
                    help='template space and its resolution')           

parser.add_argument('--fsl_spaces',  dest='fsl_spaces', nargs='*', default=[], 
                    help='checks if fsl FLIRT and FNIRT files are there')

parser.add_argument('--participants_list', dest='participants_list',                      
                    help='path to participants list (csv or tsv')

args = parser.parse_args()

def check_fmriprep(subject_dir, participant_id, ses_id, run_id, tpl_spaces, modality):    
    fmriprep_files_dict = fmriprep_modality_file_dict[modality]
    status_dict = {}
    for tpl_space in tpl_spaces:
        status_msg = "Pass"
        for k,v in fmriprep_files_dict.items():
            if status_msg == "Pass":    
                for file_suffix in [f"space-{tpl_space}_{v}"]:
                    if run_id == None:
                        filepath = Path(f"{subject_dir}/{ses_id}/{modality}/{participant_id}_{ses_id}_{file_suffix}")
                    else:
                        if modality == "anat":
                            filepath = Path(f"{subject_dir}/{ses_id}/{modality}/{participant_id}_{ses_id}_{run_id}_{file_suffix}")
                        else:
                            filepath = Path(f"{subject_dir}/{ses_id}/{modality}/{participant_id}_{ses_id}_task-{TASK}_{run_id}_{file_suffix}")
    
                    filepath_status = Path.is_file(filepath)
                    if not filepath_status:
                        # print(filepath) 
                        status_msg = f"{file_suffix} not found"
                        status_dict[tpl_space] = status_msg
                        break

                status_dict[tpl_space] = status_msg
            else:
                break

    return status_dict

def check_fsl(subject_dir, participant_id, ses_id, fsl_spaces):
    status_dict = {}
    for fsl_space in fsl_spaces:
        status_msg = "Pass"
        for k,v in fsl_files_dict.items():
            if status_msg == "Pass":
                for file_suffix in [f"space-{fsl_space}_{v}"]:
                    filepath = Path(f"{subject_dir}/{ses_id}/anat/{participant_id}_{ses_id}_{file_suffix}")
                    filepath_status = Path.is_file(filepath)
                    if not filepath_status:
                        print(filepath)
                        status_msg = f"{file_suffix} not found"
                        status_dict[fsl_space] = status_msg
                        break
                status_dict[fsl_space] = status_msg
            else:
                break

    return status_dict

def check_output(subject_dir, participant_id, ses_id, run_id, tpl_spaces, fsl_spaces, modalities):
    fmriprep_status_dict = {}
    for modality in modalities:
        fmriprep_status_dict[modality] = check_fmriprep(subject_dir, participant_id, ses_id, run_id, tpl_spaces, modality)
    
    if len(fsl_spaces) > 0:
        fsl_status_dict = check_fsl(subject_dir, participant_id, ses_id, fsl_spaces)
    else:
        fsl_status_dict = {}
        for fsl_space in fsl_spaces:
            fsl_status_dict[fsl_space] = "Not checked"

    return fmriprep_status_dict, fsl_status_dict

if __name__ == "__main__":
    # Read from csv
    fmriprep_dir = args.fmriprep_dir
    ses = f"ses-{args.ses}"
    run = f"run-{args.run}"
    tpl_spaces = args.tpl_spaces
    fsl_spaces = args.fsl_spaces
    participants_list = args.participants_list
    status_log_dir = fmriprep_dir + "/status_logs/"
    modalities = MODALITIES

    if not Path.is_dir(Path(status_log_dir)):
        os.mkdir(status_log_dir)

    print(f"\nChecking subject ids and dirs...")
    # Check number of participants from the list
    if participants_list.rsplit(".")[1] == "tsv":
        participants_df = pd.read_csv(participants_list,sep="\t")
    else:
        participants_df = pd.read_csv(participants_list)

    participant_ids = participants_df["participant_id"]
    participant_ids = ["sub-" + str(id) for id in participant_ids]
    n_participants = len(participant_ids)
    print(f"Number of subjects in the participants list: {n_participants}")

    # Check available subject dirs
    subject_path_list = glob.glob(f"{fmriprep_dir}/sub*[!html]")
    subject_dir_list = [os.path.basename(x) for x in subject_path_list]
    
    print(f"Number of fmriprep_dir subject dirs: {len(subject_path_list)}")
    
    fmriprep_participants = set(participant_ids) & set(subject_dir_list)
    subjects_missing_subject_dir = set(participant_ids) - set(subject_dir_list)
    subjects_missing_in_participant_list = set(subject_dir_list) - set(participant_ids)

    print(f"\nSubjects missing FMRIPrep subject_dir: {len(subjects_missing_subject_dir)}")
    print(f"Subjects missing in participant list: {len(subjects_missing_in_participant_list)}")
    print(f"\nChecking FMRIPrep output for {len(fmriprep_participants)} subjects")

    fmriprep_tpl_spaces= []
    fmriprep_complete_cols = []
    for modality in modalities:
        modality_tpl_spaces = [f"{modality}-{tpl_space}" for tpl_space in tpl_spaces]
        fmriprep_tpl_spaces += modality_tpl_spaces
        fmriprep_complete_cols.append(f"{modality}-fmriprep_complete")

    status_cols = fmriprep_tpl_spaces + [f"fsl-{s}" for s in fsl_spaces]
    status_df = pd.DataFrame(columns=["participant_id"] + fmriprep_complete_cols + status_cols)

    # populate status_df iterating over available FS subject dirs
    for p, participant_id in enumerate(fmriprep_participants):
        subject_dir = f"{fmriprep_dir}/{participant_id}"
        modality_status_dict, fsl_status = check_output(subject_dir, participant_id, ses, run, tpl_spaces, fsl_spaces, modalities)
        fmriprep_status = []
        fmriprep_complete = []
        for modality in modalities:
            modality_status = modality_status_dict[modality]
            modality_complete = all(flag == "Pass" for flag in modality_status.values())
            fmriprep_status += list(modality_status.values())
            fmriprep_complete.append(modality_complete)

        status_df.loc[p] = [participant_id] + fmriprep_complete + fmriprep_status + list(fsl_status.values())
        
    # append subjects missing FS subject_dir
    for p, participant_id in enumerate(subjects_missing_subject_dir):
        subject_dir = f"{fmriprep_dir}/{participant_id}"
        status_list = len(status_cols)*["subject dir not found"]
        fmriprep_complete = len(status_cols)*[False]
        fmriprep_status = len(status_cols)*["Not checked"]
        status_df.loc[p + len(participant_ids)] = [participant_id] + fmriprep_complete + fmriprep_status + list(fsl_status.values())

    status_df["fmriprep_complete"] = status_df[fmriprep_complete_cols].prod(axis=1).astype(bool)
    n_complete = len(status_df[status_df["fmriprep_complete"]])
    n_failed = n_participants - n_complete

    print(f"\nnumber of failed subjects: {n_failed}")

    if n_failed > 0:
        failed_participant_ids = status_df[status_df["fmriprep_complete"]==False]["participant_id"].values
        subject_list = f"{status_log_dir}/failed_subject_ids.txt"
        with open(f'{subject_list}', 'w') as f:
            for line in failed_participant_ids:
                f.write(f"{line}\n")
        print(f"See failed subject list: {subject_list}")

    if len(subjects_missing_in_participant_list) > 0:
        subject_list = f"{status_log_dir}/subjects_missing_in_participant_list.txt"
        with open(f'{subject_list}', 'w') as f:
            for line in subjects_missing_in_participant_list:
                f.write(f"{line}\n")
        print(f"See subjects_missing_in_participant_list: {subject_list}")
    
    # Save fs_status_df
    status_save_path = f"{status_log_dir}/fmriprep_status.csv"
    print(f"See fmriprep status csv: {status_save_path}")
    status_df.to_csv(status_save_path)