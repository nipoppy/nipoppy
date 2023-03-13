import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import glob
from bids import BIDSLayout 
import os


HELPTEXT = """
Script to check participant-session availability 
"""
#Author: nikhil153
#Date: 1-Dec-2022 

modality_suffic_dict = {
    "anat": "T1w",
    "dwi": "dwi"
}

# argparse
parser = argparse.ArgumentParser(description=HELPTEXT)

# data
parser.add_argument('--bids_dir', help='path to bids_dir with all the subjects')
parser.add_argument('--modalities', nargs='*', default=["anat"], 
                    help='modalities to check') 
parser.add_argument('--file_ext', default='nii.gz', help='file extension to query')
parser.add_argument('--output_csv', help='path to output csv file')

args = parser.parse_args()
bids_dir = args.bids_dir
modalities = args.modalities
file_ext = args.file_ext

print(f"Validating output in: {modalities}")

output_csv = args.output_csv
participants_tsv = f"{bids_dir}/participants.tsv"

# Check participants tsv and actual participant dirs
tsv_participants = set(pd.read_csv(participants_tsv,sep="\t")["participant_id"].values)
bids_dir_paths = glob.glob(f"{bids_dir}/sub*")
bids_dir_participants = set([os.path.basename(x) for x in bids_dir_paths])

participants_missing_in_tsv = list(bids_dir_participants - tsv_participants)
participants_missing_in_bids_dir = list(tsv_participants - bids_dir_participants)

print(f"n_participants_tsv: {len(tsv_participants)}, \
        n_participants_bids_dir: {len(bids_dir_participants)}, \
        n_participants_missing_in_tsv: {len(participants_missing_in_tsv)}, \
        n_participants_missing_in_bids_dir: {len(participants_missing_in_bids_dir)}")

if tsv_participants == bids_dir_participants:
    layout = BIDSLayout(bids_dir)
    sessions = layout.get_sessions()

    bids_status_df = pd.DataFrame()    
    for participant in tsv_participants:
        participant_id = participant.split("-",2)[1]

        session_df = pd.DataFrame(index=sessions, columns=modalities)
        for ses in sessions:
            f_count = []
            for modality in modalities:
                file_suffix = modality_suffic_dict[modality]
                f = layout.get(subject=participant_id, 
                                        session=ses, 
                                        extension=file_ext, 
                                        suffix=file_suffix,                 
                                        return_type='filename')
                
                f_count.append(len(f))

            session_df.loc[ses] = f_count

        session_df = session_df.reset_index().rename(columns={"index":"session_id"})
        session_df["participant_id"] = participant
        bids_status_df = bids_status_df.append(session_df)

    print(f"Saving bids_status_df at {output_csv}")        
    bids_status_df = bids_status_df.set_index("participant_id")
    bids_status_df.to_csv(output_csv)

else:
    print(f"participants_tsv and bids_dir participants mismatch...")
    output_csv = os.path.join(os.path.dirname(output_csv) + "/mismatched_participants.csv")
    missing_tsv_status = len(participants_missing_in_tsv) * ["participants_missing_in_tsv"]
    missing_bids_status = len(participants_missing_in_bids_dir) * ["participants_missing_in_bids_dir"]
    missing_df = pd.DataFrame()
    missing_df["participant_id"] = participants_missing_in_tsv + participants_missing_in_bids_dir
    missing_df["status"] = missing_tsv_status + missing_bids_status
    print(f"Saving missing participants csv at {output_csv}")
    missing_df.to_csv(output_csv,index=None)
