import pandas as pd
import numpy as np
import json
import argparse
from utils import *

#Author: nikhil153
#Date: 07-Oct-2022

# argparse
HELPTEXT = """
Script to perform DICOM to BIDS conversion using HeuDiConv
"""

def run(instrument_config):
    config = get_norming_config(instrument_config)

    instrument = config["instrument"]
    data_paths = config["data_paths"]
    stratification = config["stratification"]

    norming_procedure = instrument["norming_procedure"]

    raw_score_name = instrument["raw_score_name"]
    normed_score_name = instrument["normed_score_name"]

    participant_id_col = data_paths["participant_id_column"]

    stratification[raw_score_name] = {"dtype": instrument["dtype"]}
    strata_cols = list(stratification.keys())

    print("-"*80)
    print("Starting score normalization process...\n")
    print(f"Instrument name: {raw_score_name}")
    print(f"Using {strata_cols} as stratification columns\n")
    print("-"*60)
    print("***IMPORTANT: Instrument and demograhic column names should match in the raw data sheet and the baseline score sheet***")
    print("-"*60)
    print("")

    raw_data_df = read_raw_scores(data_paths)
    baseline_df = read_baseline_scores(data_paths)

    raw_data_df = raw_data_df[[participant_id_col] + strata_cols]
    raw_data_df = raw_data_df.set_index(participant_id_col)
    valid_data_df = get_valid_scores(raw_data_df,instrument)

    n_participants_to_normalized = len(valid_data_df)
    print(f"\nn_participants to be normalized: {n_participants_to_normalized}")

    baseline_df, baselines_ranges = format_baseline_scores(baseline_df, stratification, raw_score_name)
    n_strata = len(baseline_df)

    print("-"*60)
    print(f"n_starta: {n_strata}")
    print(f"starta ranges:\n{baselines_ranges}\n")
    print(f"***IMPORTANT: Any raw scores beyond these ranges will not be normalized***")
    print("-"*60)

    print(f"Starting score normalization based on {norming_procedure}...")
    normed_data_df = valid_data_df.copy()
    for idx, participant_data in normed_data_df.iterrows():
        normed_score, note = get_normed_score(participant_data, baseline_df, stratification, raw_score_name, norming_procedure)
        normed_data_df.loc[idx,normed_score_name] = normed_score
        normed_data_df.loc[idx,"note"] = note

    participants_missing_matches = list(normed_data_df[normed_data_df[normed_score_name].isna()].index)
    n_missing_matches = len(participants_missing_matches)

    print(f"\nParticipants (n={n_missing_matches}) are missing stratification matches")
    print("-"*60)

    # Save data
    normed_data = data_paths["normed_data"]
    normed_sheet = data_paths["normed_sheet"]

    print(f"Saving normed data to: {normed_data}")
    save_df = pd.merge(raw_data_df[strata_cols], 
                        normed_data_df[strata_cols + [normed_score_name, "note"]], 
                    on=[participant_id_col] + strata_cols, how="left")

    save_df.to_excel(normed_data, sheet_name=normed_sheet)
    print(f"Norming procedure completed for {raw_score_name}")
    print("-"*80)

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to perform Neuropysch score normalization
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--instrument_config', type=str, help='path to instrument config json file')
    args = parser.parse_args()

    instrument_config = args.instrument_config
    run(instrument_config)
