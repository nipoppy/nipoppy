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
Script to generate list of subjects (and their bids_id) to be added to the mr_proc dicom directory
"""

parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--recruit_manifest', type=str, help='participant_manifest from study coordinator')
parser.add_argument('--bids_dir', type=str, help='path to the current bids_dir')
parser.add_argument('--loris_imaging_manifest', type=str, help='loris_imaging_manifest for crossreference')
parser.add_argument('--visit', type=str, help='visit label (i.e. session in BIDS')
parser.add_argument('--release_dir', type=str, help='path to directory to save lists and logs during dicom refresh')
args = parser.parse_args()

recruit_manifest = args.recruit_manifest
bids_dir = args.bids_dir
loris_imaging_manifest = args.loris_imaging_manifest
visit = args.visit
release_dir = args.release_dir

# Total recruitment till date
recruit_df = pd.read_csv(recruit_manifest)
participants_recruit = set(recruit_df["participant_id"].str.strip())
n_participants_recruit = len(participants_recruit)
print(f"Number of total recruited participants: {n_participants_recruit}")

# Current BIDSified participants (e.g. sub-PD01234D123456)
id_len = 7 
bids_participants_tsv = f"{bids_dir}/participants.tsv"
bids_participants_df = pd.read_csv(bids_participants_tsv, sep="\t")
participants_bids = set(bids_participants_df["participant_id"].str.split("-",expand=True)[1].str.slice(stop=id_len).str.strip())
n_participants_bids = len(participants_bids)
print(f"Number of total BIDSified participants: {n_participants_bids}")

# Current participants in LORIS 
# (this helps to match DICOM IDs when there are multiple hits on dicom server)
loris_df = pd.read_csv(loris_imaging_manifest)
loris_df = loris_df[loris_df["Vist Label"]==visit]
participants_loris = set(loris_df["PSCID"].str.strip())
n_participants_loris = len(participants_loris)
print(f"Number of total LORIS (imaging) participants: {n_participants_loris}")

# Identify new participants
participants_new = participants_recruit - participants_bids
n_participants_new = len(participants_new)
print(f"Number of new participants: {n_participants_new}")

# Generate BIDS_ID for the new participants
participants_new_in_loris = participants_new & participants_loris
n_participants_new_in_loris = len(participants_new_in_loris)

participants_new_not_in_loris = participants_new - participants_loris
n_participants_new_not_in_loris = len(participants_new_not_in_loris)

print(f"Number of new participants in LORIS: {n_participants_new_in_loris}")
print(f"Number of new participants NOT in LORIS: {n_participants_new_not_in_loris}")

if n_participants_new_in_loris > 0:
    loris_new_df = loris_df[loris_df["PSCID"].isin(participants_new_in_loris)][["PSCID","DCCID"]].copy()
    loris_new_df["bids_id"] = loris_df["PSCID"].astype(str) + "D" + loris_df["DCCID"].astype(str)
    loris_new_df["participant_id"] = loris_new_df["PSCID"]
    loris_new_df = loris_new_df[["participant_id","bids_id"]]
    loris_new_df.to_csv(f"{release_dir}/participants_bids_id.csv",index=None)
else:
    print("No new participants are in LORIS - bids_ids cannot be generated at the moment")
