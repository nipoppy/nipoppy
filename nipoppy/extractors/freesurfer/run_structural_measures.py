import numpy as np
import pandas as pd
import json
import os
import glob
import argparse
import brainload as bl
from nipoppy.workflow.utils import (
    COL_CONV_STATUS,
    COL_SESSION_MANIFEST,
    COL_BIDS_ID_MANIFEST,
)

# Globals
# Brainload has two separate functions to extract aseg data. 
measure_column_names = ["StructName","Structure","Description","Volume_mm3", "unit"]

def get_aseg_stats(participant_stats_dir, aseg_cols):
    """ Parses the aseg.stats file
    """
    aseg_cols = ["StructName", "Volume_mm3"]
    aseg_stats = bl.stat(f'{participant_stats_dir}/aseg.stats')
    table_df = pd.DataFrame(aseg_stats["table_data"], columns=aseg_stats["table_column_headers"])[aseg_cols]
    measure_df = pd.DataFrame(data=aseg_stats["measures"], columns=measure_column_names)[aseg_cols]
    _df = pd.concat([table_df,measure_df],axis=0)
    return _df

def get_DKT_stats(participant_stats_dir, dkt_cols, parcel="aparc.DKTatlas"):
    """ Parses the <>.aparc.DKTatlas.stats file
    """
    hemi = "lh"
    stat_file = f"{hemi}.{parcel}.stats"
    lh_dkt_stats = bl.stat(f'{participant_stats_dir}/{stat_file}')
    lh_df = pd.DataFrame(lh_dkt_stats["table_data"], columns=lh_dkt_stats["table_column_headers"])[dkt_cols]
    lh_df["hemi"] = hemi

    hemi = "rh"
    stat_file = f"{hemi}.{parcel}.stats"
    rh_dkt_stats = bl.stat(f'{participant_stats_dir}/{stat_file}')
    rh_df = pd.DataFrame(rh_dkt_stats["table_data"], columns=rh_dkt_stats["table_column_headers"])[dkt_cols]
    rh_df["hemi"] = hemi
    
    _df = pd.concat([lh_df,rh_df], axis=0)

    return _df

HELPTEXT = """
Script to parse and collate FreeSurfer stats files across subjects
"""

parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--global_config', type=str, help='path to global configs for a given nipoppy dataset', required=True)
parser.add_argument('--FS_config', type=str, help='path to freesurfer configs for a given nipoppy dataset', required=True)
parser.add_argument('--participants_list', default=None, help='path to participants list (csv or tsv')
parser.add_argument('--session_id', type=str, help='session id for the participant', required=True)    
parser.add_argument('--output_dir', default=None, help='path to save extracted output (default: derivatives/freesurfer/<version>/IDP/<session>)')

args = parser.parse_args()

global_config_file = args.global_config
FS_config_file = args.FS_config
participants_list = args.participants_list
session_id = args.session_id
session = f"ses-{session_id}"
output_dir = args.output_dir

# Read global configs
with open(global_config_file, 'r') as f:
    global_configs = json.load(f)

# Read FS configs
with open(FS_config_file, 'r') as f:
    FS_configs = json.load(f)

DATASET_ROOT = global_configs["DATASET_ROOT"]
FS_version = FS_configs["version"]
stat_configs = FS_configs["stat_configs"]
stat_config_names = stat_configs.keys()

print(f"Using dataset root: {DATASET_ROOT} and FreeSurfer version: v{FS_version}")
print(f"Using stat configs: {stat_config_names}")

if output_dir == None:
    output_dir = f"{DATASET_ROOT}/derivatives/freesurfer/v{FS_version}/IDP/{session}/"

if participants_list == None:
    # use doughnut
    doughnut_file = f"{DATASET_ROOT}/scratch/raw_dicom/doughnut.csv"
    doughnut_df = pd.read_csv(doughnut_file)
    doughnut_df[COL_CONV_STATUS] = doughnut_df[COL_CONV_STATUS].astype(bool)
    bids_participants = doughnut_df[(doughnut_df[COL_SESSION_MANIFEST]==session) & (doughnut_df[COL_CONV_STATUS])][COL_BIDS_ID_MANIFEST].unique()
    n_bids_participants = len(bids_participants)
    print(f"Running all {n_bids_participants} participants in doughnut with session: {session}")
else:
    # use custom list 
    bids_participants = list(pd.read_csv(participants_list)["participant_id"])

    n_bids_participants = len(bids_participants)
    print(f"Running {n_bids_participants} participants from the list with session: {session}")


# Extract stats for each participant
fs_output_dir = f"{DATASET_ROOT}/derivatives/freesurfer/v{FS_version}/output/{session}/"

aseg_df = pd.DataFrame()
dkt_df = pd.DataFrame()
for participant_id in bids_participants:
    participant_stats_dir = f"{fs_output_dir}{participant_id}/stats/"
    print(f"Extracting stats for participant: {participant_id}")
    
    for config_name, config_cols in stat_configs.items():
        print(f"Extracting data for config: {config_name}")
        if config_name.strip().lower() == "aseg":
            try:
                _df = get_aseg_stats(participant_stats_dir, config_cols) 
                # transpose it to wideform               
                names_col = config_cols[0]
                values_col = config_cols[1]                
                cols = ["participant_id"] + list(_df[names_col].values)
                vals = [participant_id] + list(_df[values_col].values)                
                _df_wide = pd.DataFrame(columns=cols)
                _df_wide.loc[0] = vals
                aseg_df = pd.concat([aseg_df,_df_wide], axis=0)
            
            except:
                print(f"Error parsing aseg data for {participant_id}")

        elif config_name.strip().lower() == "dkt":
            try:
                _df = get_DKT_stats(participant_stats_dir, config_cols)
                # transpose it to wideform               
                names_col = config_cols[0]
                values_col = config_cols[1]                
                cols = ["participant_id"] + list(_df["hemi"] + "." + _df[names_col])
                vals = [participant_id] + list(_df[values_col])                
                _df_wide = pd.DataFrame(columns=cols)
                _df_wide.loc[0] = vals
                dkt_df = pd.concat([dkt_df,_df_wide], axis=0)

            except Exception as e:
                print(f"Error parsing dkt data for {participant_id} with exception: {e}")
            
        else:
            print(f"Unknown stat config: {config_name}")

# Save configs
print(f"Saving collated stat tables at: {output_dir}")
aseg_csv = f"{output_dir}/aseg.csv"
dkt_csv = f"{output_dir}/dkt.csv"

if len(aseg_df) > 0: 
    aseg_df.to_csv(aseg_csv, index=None)
else:
    print("aseg_df is empty")

if len(dkt_df) > 0:
    dkt_df.to_csv(dkt_csv, index=None)
else:
    print("dkt_df is empty")