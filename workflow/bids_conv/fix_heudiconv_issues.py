import argparse
import json
import shutil
import pandas as pd
import glob
import numpy as np
import regex as re
import os

# Known issues:
# 1. fmap: multi-echo fieldmap dicoms get converted as:
#   "<prefix>_echo-1_part-mag_epi.<nii.gz/json>", "<prefix>_echo-1_part-phase_epi.<nii.gz/json>", 
#   "<prefix>_echo-2_part-mag_epi.<nii.gz/json>", "<prefix>_echo-2_part-phase_epi.<nii.gz/json>".
#   They need to be renamed as 
#   "<prefix>_magnitude1.<nii.gz/json>", "<prefix>_phase1.<nii.gz/json>"
#   "<prefix>_magnitude2.<nii.gz/json>", "<prefix>_phase2.<nii.gz/json>"

# fmap PhaseEncodingDirection:
# File "/usr/local/miniconda/lib/python3.7/site-packages/sdcflows/workflows/base.py", line 123, in init_sdc_estimate_wf
# 'PhaseEncodingDirection is not defined within the metadata retrieved '
# Solution: https://neurostars.org/t/phase-encoding-error-for-field-maps/2650/3: 
# "If you BOLD series is j, then your EPI fieldmap should be j-, and vice versa"

# 2. asl: remove asl and m0 scans from scans.tsv since they are added in the .bidsignore file for now. 

HELPTEXT = """
Script to perform DICOM to BIDS conversion using HeuDiConv
"""
#Author: nikhil153
#Date: 07-Oct-2022

# argparse
parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--session_id', type=str, help='session id for the participant')
parser.add_argument('--issue_type', type=str, help='name of the issue to be resolved. See list at the top of this script')

args = parser.parse_args()

global_config = args.global_config
session_id = args.session_id
issue_type = args.issue_type

# Read global configs
f = open(global_config)
json_data = json.load(f)

DATASET_ROOT = json_data["DATASET_ROOT"]
BIDS_DIR = F"{DATASET_ROOT}/bids/"
participants_df = pd.read_csv(f"{BIDS_DIR}/participants.tsv", sep="\t")

participants_list = participants_df["participant_id"].values
print(f"\nNumber of participants listed: {len(participants_list)}")


if issue_type == "fmap":
    # Rename scans
    part_name_dict = {"mag":"magnitude","phase":"phase"}
    echo_list = [1,2]
    ext_f_list = ["nii.gz", "json"]

    print(f"\nStarting fmap renaming ...")
    for participant_id in participants_list:
        print(f"\nparticitpant id: {participant_id}")
        fmap_dir = f"{BIDS_DIR}{participant_id}/ses-{session_id}/fmap/"
        fmap_rename_dict = {}
        for echo in echo_list:
            for ext_f in ext_f_list:
                for src_part, dst_part in part_name_dict.items():
                    src_f = glob.glob(f"{fmap_dir}{participant_id}_ses-{session_id}_*_echo-{echo}_part-{src_part}_epi.{ext_f}")[0]
                    # initializing Substring
                    sub_str = f"ses-{session_id}_(.*)_echo"
                    # Wildcard search to find optional substrings in the filename (e.g. acq-<>_run-<> etc)
                    temp = re.compile(sub_str)
                    src_substring_match = temp.search(src_f).group(1)                               
                    dst_f = f"{fmap_dir}{participant_id}_ses-{session_id}_{src_substring_match}_{dst_part}{echo}.{ext_f}"
                    
                    fmap_rename_dict[f"fmap/{os.path.basename(src_f)}"] = f"fmap/{os.path.basename(dst_f)}"
                    # Rename the file
                    try: 
                        shutil.move(src_f, dst_f)
                    except Exception as ex:
                        print(ex)

        # Update scans.tsv
        print(f"Updating scans.tsv ...")
        scans_tsv = f"{BIDS_DIR}/{participant_id}/ses-{session_id}/{participant_id}_ses-{session_id}_scans.tsv"
        scans_df = pd.read_csv(scans_tsv,sep="\t")
        scans_df["filename"] = scans_df["filename"].replace(fmap_rename_dict)        
        scans_df["operator"] = "n/a"
        scans_df.to_csv(scans_tsv, sep="\t",index=None)

    print(f"\nfmap renaming completed ...")
   
elif issue_type == "asl":
    print(f"\nStarting asl filename removal from scans.tsv ...")
    for participant_id in participants_list:
        print(f"\nparticitpant id: {participant_id}")
        scans_tsv = f"{BIDS_DIR}/{participant_id}/ses-{session_id}/{participant_id}_ses-{session_id}_scans.tsv"
        scans_df = pd.read_csv(scans_tsv,sep="\t")
        indexASL = scans_df[(scans_df['filename'].str.contains("asl")) | scans_df['filename'].str.contains("m0scan")].index
        scans_df = scans_df.drop(indexASL)                
        scans_df["operator"] = "n/a"        
        scans_df.to_csv(scans_tsv, sep="\t",index=None)

    print(f"\asl filename removal from scans.tsv completed ...")
else:
    print(f"{issue_type} not yet supported")