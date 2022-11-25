import argparse
import pandas as pd
import numpy as np
import glob
import os
from pathlib import Path

#Author: nikhil153
#Date: 22-Nov-2022

# argparse
HELPTEXT = """
Script to organize (copy or symlink) raw DICOMs with BIDS complient naming. 
"""

parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--dicom_source_dir', type=str, help='path to raw dicom source')
parser.add_argument('--dicom_dest_dir', type=str, help='path to mr_proc dicom dir')
parser.add_argument('--participant_bids_csv', type=str, help='participant_bids_csv')

args = parser.parse_args()

dicom_source_dir = args.dicom_source_dir
dicom_dest_dir = args.dicom_dest_dir
participant_bids_csv = args.participant_bids_csv

participant_df = pd.read_csv(participant_bids_csv)
participant_df = participant_df[["participant_id","bids_id"]].copy() #drop previously linked_dicom_dir column
n_participants = len(participant_df)

print(f"Number of subjects in the batch: {n_participants}")

print(f"Symlinking dicom dirs from {dicom_source_dir} to {dicom_dest_dir}")

dicom_dir_list = []
n_max_dcm_list = []
for index, row in participant_df.iterrows():
    participant_id = row['participant_id']
    bids_id = row['bids_id']

    print(f"\nparticipant_id: {participant_id}, bids_id: {bids_id}")
    dicom_dir_matches = glob.glob(f"{dicom_source_dir}/{participant_id}*")

    if len(dicom_dir_matches) > 1:
        print(f"Found multiple ({len(dicom_dir_matches)}) dicom dirs")
        n_dcm_list = []

        for dicom_dir in dicom_dir_matches:
            n_dcm = len(os.listdir(dicom_dir))
            n_dcm_list.append(n_dcm)

        n_max_dcm = np.max(n_dcm_list)
        print(f"Selecting dicom dir with {n_max_dcm} dcm files")
        max_n_dicom_dir = dicom_dir_matches[np.argmax(n_dcm_list)]
        link_dicom_dir = max_n_dicom_dir
    else:
        link_dicom_dir = dicom_dir_matches[0]
        n_max_dcm = len(os.listdir(link_dicom_dir))

    dicom_dir_list.append(os.path.basename(link_dicom_dir))
    n_max_dcm_list.append(n_max_dcm)
    print(f"Creating symlink from {os.path.basename(link_dicom_dir)} to {bids_id}")
    os.symlink(link_dicom_dir, f"{dicom_dest_dir}/{bids_id}")

participant_df["linked_dicom_dir"] = dicom_dir_list
participant_df["n_dcm"] = n_max_dcm_list
participant_df.to_csv(participant_bids_csv)
print("\nSymlinking completed")