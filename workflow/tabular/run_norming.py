import pandas as pd
import numpy as np
import json
import argparse
import workflow.logger as my_logger
from utils import *

#Author: nikhil153
#Date: 01-Jun-2023

HELPTEXT = """
Script to perform DICOM to BIDS conversion using HeuDiConv
"""

def run_contrast_norming(instrument_config, logger):
    """ Special function to calculate contrast based norming
    """
    config = get_norming_config(instrument_config)
    instrument = config["instrument"]
    data_paths = config["data_paths"]
    stratification = config["stratification"]
    normed_score_name = instrument["normed_score_name"]
    participant_id_col = data_paths["participant_id_column"]
    
    # Check if it's a valid contrast config
    try:
        raw_score_A_name = instrument["raw_score_A_name"]
        raw_score_B_name = instrument["raw_score_B_name"]
        regress_model_dict = instrument["regression_model_coefficients"]
        
    except Exception as e:
        logger.error(f"Invalid contrast norming json. Exception: {e}")
        return pd.DataFrame()
    
    # Add score columns to stratification to simplify dataframe slicing
    stratification[raw_score_A_name] = {"dtype": instrument["dtype"]}
    stratification[raw_score_B_name] = {"dtype": instrument["dtype"]}
    strata_cols = list(stratification.keys())

    logger.info("-"*80)
    logger.info("Starting contrast normalization process...")
    logger.info(f"Instrument names: {raw_score_A_name}, {raw_score_B_name}")
    logger.info(f"participant_id_col: {participant_id_col}")
    logger.info(f"Using {strata_cols} as stratification columns")
    logger.info("-"*60)

    logger.info("Reading raw scores")
    raw_data_df = read_raw_scores(data_paths)
    
    raw_data_df = raw_data_df[[participant_id_col] + strata_cols]
    raw_data_df = raw_data_df.set_index(participant_id_col)
    raw_data_df[raw_score_A_name] = raw_data_df[raw_score_A_name].astype(float)
    raw_data_df[raw_score_B_name] = raw_data_df[raw_score_B_name].astype(float)

    # Validate in series (i.e. filter based on score A and then pipe that to filter based on score B)
    logger.info("Checking valid scores")
    valid_data_A_df = get_valid_scores(raw_data_df,instrument,logger,raw_score_name="raw_score_A_name")
    valid_data_B_df = get_valid_scores(valid_data_A_df,instrument,logger,raw_score_name="raw_score_B_name")
    valid_data_df = valid_data_B_df.copy()

    n_participants_to_normalized = len(valid_data_df)
    logger.info(f"n_participants to be normalized: {n_participants_to_normalized}")

    logger.info(f"Starting contrast score normalization using hidden variables and regression model...")
    normed_data_df = valid_data_df.copy()
    for idx, participant_data in normed_data_df.iterrows():
        normed_score, HV_scores = get_contrast_normed_score(participant_data, stratification, raw_score_A_name, 
                                                            raw_score_B_name, regress_model_dict)
        hidden_score_names = list(HV_scores.keys())
        hidden_score_vals = list(HV_scores.values())
        print(hidden_score_vals)
        normed_data_df.loc[idx,hidden_score_names] = hidden_score_vals
        normed_data_df.loc[idx,normed_score_name] = normed_score
        normed_data_df.loc[idx,"note"] = "contrast norming"

    participants_missing_matches = list(normed_data_df[normed_data_df[normed_score_name].isna()].index)
    n_missing_matches = len(participants_missing_matches)

    logger.warning(f"Participants (n={n_missing_matches}) are missing stratification matches")
    logger.info("-"*60)
    logger.info(f"Contrast norming procedure completed for {raw_score_A_name} and {raw_score_B_name}")
    logger.info("-"*80)

    save_df = pd.merge(raw_data_df[strata_cols], 
                       normed_data_df[strata_cols + hidden_score_names + [normed_score_name, "note"]], 
                       on=[participant_id_col] + strata_cols, how="left") 
    
    return save_df

def run_variable_norming(instrument_config, logger):
    """ main run script to normalize raw scores
    """
    config = get_norming_config(instrument_config)

    instrument = config["instrument"]
    data_paths = config["data_paths"]
    stratification = config["stratification"]

    norming_procedure = instrument["norming_procedure"]
    if norming_procedure.lower() in ["regress", "regression"]:
        regress_model_dict = instrument["regression_model_coefficients"]
    else:
        regress_model_dict = None

    raw_score_name = instrument["raw_score_name"]
    normed_score_name = instrument["normed_score_name"]
    participant_id_col = data_paths["participant_id_column"]

    stratification[raw_score_name] = {"dtype": instrument["dtype"]}
    strata_cols = list(stratification.keys())

    logger.info("-"*80)
    logger.info("Starting score normalization process...")
    logger.info(f"Instrument name: {raw_score_name}")
    logger.info(f"participant_id_col: {participant_id_col}") 
    logger.info(f"Using {strata_cols} as stratification columns")
    logger.info("-"*60)
    logger.info("***IMPORTANT: Instrument and demograhic column names should match in the raw data sheet and the baseline score sheet***")
    logger.info("-"*60)
    logger.info("")

    logger.info("Reading raw scores")
    raw_data_df = read_raw_scores(data_paths)

    raw_data_df = raw_data_df[[participant_id_col] + strata_cols]
    raw_data_df = raw_data_df.set_index(participant_id_col)

    raw_data_df[raw_score_name] = raw_data_df[raw_score_name].astype(float)

    logger.info("Checking valid scores")
    valid_data_df = get_valid_scores(raw_data_df,instrument,logger)

    n_participants_to_normalized = len(valid_data_df)
    logger.info(f"n_participants to be normalized: {n_participants_to_normalized}")

    if norming_procedure.lower() in ["regress", "regression"]:
        logger.info(f"Baseline score tables are NOT used during norming for {norming_procedure}")
        baseline_df = None
    else:
        logger.info("Reading baseline scores")
        baseline_df = read_baseline_scores(data_paths)
        baseline_df, baselines_ranges = format_baseline_scores(baseline_df, stratification, raw_score_name)
        n_strata = len(baseline_df)
        logger.info("-"*60)
        logger.info(f"n_starta: {n_strata}")
        logger.info(f"starta ranges:{baselines_ranges}")
        logger.warning(f"***IMPORTANT: Any raw scores beyond these ranges will not be normalized***")
        logger.info("-"*60)

    logger.info(f"Starting score normalization based on {norming_procedure}...")
    normed_data_df = valid_data_df.copy()
    for idx, participant_data in normed_data_df.iterrows():
        normed_score, note = get_normed_score(participant_data, baseline_df, stratification, raw_score_name, 
                                            logger, norming_procedure, regress_model_dict)
        normed_data_df.loc[idx,normed_score_name] = normed_score
        normed_data_df.loc[idx,"note"] = note

    participants_missing_matches = list(normed_data_df[normed_data_df[normed_score_name].isna()].index)
    n_missing_matches = len(participants_missing_matches)

    logger.warning(f"Participants (n={n_missing_matches}) are missing stratification matches")
    logger.info("-"*60)
    logger.info(f"Norming procedure completed for {raw_score_name}")
    logger.info("-"*80)

    save_df = pd.merge(raw_data_df[strata_cols], 
                       normed_data_df[strata_cols + [normed_score_name, "note"]], 
                       on=[participant_id_col] + strata_cols, how="left")

    return save_df

# Save data
def save_normed_data(instrument_config, save_df, logger):
    """ Save normed dataframe to a new excel file + spreadsheet
    """
    config = get_norming_config(instrument_config)
    data_paths = config["data_paths"]
    normed_data = data_paths["normed_data"]
    normed_sheet = data_paths["normed_sheet"]

    logger.info(f"Saving normed data to: {normed_data}")
    save_df.to_excel(normed_data, sheet_name=normed_sheet)    

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to perform Neuropysch score normalization
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--instrument_config', type=str, help='path to instrument config json file')
    parser.add_argument('--contrast_norming', action='store_true', help='perform contrast norming (e.g. TMT)')

    args = parser.parse_args()

    instrument_config = args.instrument_config
    contrast_norming = args.contrast_norming

    # Create logger
    log_file = f"neuropsy_norming.log"
    logger = my_logger.get_logger(log_file)

    if contrast_norming:
        save_df = run_contrast_norming(instrument_config, logger)
    else:
        save_df = run_variable_norming(instrument_config, logger)
    
    if not save_df.empty:
        save_normed_data(instrument_config,save_df, logger)

    logger.info(f"See log here: {log_file}")
    logger.info("-"*80)