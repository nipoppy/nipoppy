import pandas as pd
import numpy as np
import json

def get_norming_config(config_file):
    """ Read config json for a given instrument
    """
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

def read_raw_scores(instrument):
    """ Read raw data tables for a specified instrument dict
    """
    raw_data = instrument["raw_data"]
    raw_sheet = instrument["raw_sheet"]    
    df = pd.read_excel(raw_data, sheet_name=raw_sheet, engine='openpyxl',header=1).dropna(axis=0,how="all")

    return df

def read_baseline_scores(instrument):
    """ Read raw data tables for a specified instrument dict
    """
    raw_data = instrument["baseline_data"]
    raw_sheet = instrument["baseline_sheet"]
    df = pd.read_excel(raw_data, sheet_name=raw_sheet, engine='openpyxl').dropna(axis=0,how="all")

    return df

def get_valid_scores(df,instrument):
    """ Check and remove out of bound or NaN scores
    """
    name = instrument["raw_score_name"]
    score_range = instrument["range"]
    nan_val = int(score_range["n/a"])
    min_val = int(score_range["min"])
    max_val = int(score_range["max"])

    n_participants = len(df)
    n_multiple_visits = len(df[df.index.duplicated()])

    n_nan_val = len(df[df[name] == nan_val])
    n_missing_val = len(df[df[name].isna()])
    print(f"n_listed_participants: {n_participants}, n_multiple_visits: {n_multiple_visits}")
    print(f"n_nan_val (i.e. {nan_val}): {n_nan_val}, n_missing_val: {n_missing_val}")
    print(f"Excluding ({n_missing_val}) participants with missing scores")
    # clean-up
    df[name] = df[name].replace({nan_val:np.NaN})
    df = df[df[name].notna()]
    
    max_available_val = np.max(df[name])
    min_available_val = np.min(df[name])

    print(f"\nPossible score range: ({min_val},{max_val})")
    print(f"Available score range: ({min_available_val},{max_available_val})")
    invalid_df = df[~df[name].isin(range(min_val, max_val+1))] # (min <= score < max)
    n_invalid_scores = len(invalid_df)
    if n_invalid_scores > 0:
        print(f"n_invalid_scores: {n_invalid_scores}")
        print(f"Using participants only with valid scores")
        df = df[df[name].isien(range(min_val, max_val+1))]

    return df
    
def format_baseline_scores(df, stratification, raw_score_name):
    """ Format baseline score sheet so it can be filtered in pandas
    """
    baselines_ranges = {}
    strata_cols = list(stratification.keys()) + [raw_score_name]

    for col in strata_cols: 
        # No need to parse categrical columns
        if (stratification[col]["dtype"].lower() == "continuous"):
            # check if column has ranges separate by "-" delimeter
            # Convention: upper limit is not include for demographics and scores: e.g. (0-4) implies {0,1,2,3}
            if df[col].str.contains("-").any():    
                df[f"{col}_min"] = df[col].astype(str).str.split("-",expand=True)[0].astype(int)
                df[f"{col}_max"] = df[col].astype(str).str.split("-",expand=True)[1]
                df.loc[df[f"{col}_max"].isna(), f"{col}_max"] = df[f"{col}_min"].astype(int) + 1 #See Convention
                df[f"{col}_max"] = df[f"{col}_max"].astype(int)  
            else:
                df[f"{col}_min"] = df[col].astype(int)
                df[f"{col}_max"] = df[col].astype(int) + 1 #See Convention
            
            baselines_ranges[col] = (np.min(df[f"{col}_min"]), np.max(df[f"{col}_max"]))
        
    return df, baselines_ranges

def get_normed_score(participant, baseline_df, stratification, raw_score_name, norming_procedure="lookup_scaled_score"):
    """ Filter baseline scores and return match for a given participant
    """
    baseline_match_df = baseline_df.copy()

    # Filter rows matching participant values
    # Convention: upper limit is not include for demographics and scores: e.g. (0-4) implies {0,1,2,3}
    for k,v in participant.items():
        if stratification[k]["dtype"] == "categorical":
            baseline_match_df = baseline_match_df[(baseline_match_df[f"{k}"] == v)]
        else:
            baseline_match_df = baseline_match_df[(baseline_match_df[f"{k}_min"] <= v) & 
                                        (baseline_match_df[f"{k}_max"] > v) ] # see convention

    # Deal with zero or > 1 matches
    if len(baseline_match_df) == 0:
        normed_score = np.nan
        note = "Strata not found"
        
    elif len(baseline_match_df) > 1:
        print(f"Multiple matches found for participant: {participant.name}, {dict(participant)}")
        print(f"Not assigning a scaled score for {participant.name}")
        normed_score = np.nan
        note = "Multiple strata matches found"

    else:
        # Select based on norming_procedure
        if norming_procedure.lower() in ["lookup_scaled_score","scaled_score"]:
            normed_score = baseline_match_df["Scaled_score"].values[0]
            note = "Scaled score"

        elif norming_procedure.lower() in ["zscore", "z-score", "z_score"]:
            participant_dict = {"raw_score":baseline_match_df[raw_score_name].values[0],
                                "Mean":baseline_match_df["Mean"].values[0],
                                "SD":baseline_match_df["SD"].values[0]}

            normed_score = z_score(participant_dict)
            note = "zscore"
        else:
            print(f"Unknown norming procedure")
            normed_score = np.nan
            note = "Unknown norming procedure"

    return normed_score, note

def z_score(participant):
    raw_score = participant["raw_score"]
    mean = participant["Mean"]
    SD = participant["SD"]
    z_score = (raw_score - mean)/SD
    return z_score
