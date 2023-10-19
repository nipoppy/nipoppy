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

def get_valid_scores(df, instrument, logger, raw_score_name="raw_score_name"):
    """ Check and remove out of bound or NaN scores
    """
    name = instrument[raw_score_name]
    score_range = instrument["range"]
    nan_val = int(score_range["n/a"])
    min_val = int(score_range["min"])
    max_val = int(score_range["max"])

    # df[name] = df[name].astype()
    n_participants = len(df)
    n_multiple_visits = len(df[df.index.duplicated()])

    n_nan_val = len(df[df[name] == nan_val])
    n_missing_val = len(df[df[name].isna()])
    logger.info(f"n_listed_participants: {n_participants}, n_multiple_visits: {n_multiple_visits}")
    logger.info(f"n_nan_val (i.e. {nan_val}): {n_nan_val}, n_missing_val: {n_missing_val}")
    logger.info(f"Excluding ({n_missing_val}) participants with missing scores")
    # clean-up
    df[name] = df[name].replace({nan_val:np.NaN})
    df = df[df[name].notna()]
    
    max_available_val = np.max(df[name])
    min_available_val = np.min(df[name])

    logger.info(f"Possible score range: ({min_val},{max_val})")
    logger.info(f"Available score range: ({min_available_val},{max_available_val})")
    invalid_df = df[(df[name] < min_val) | (df[name] > max_val)]
    n_invalid_scores = len(invalid_df)
    if n_invalid_scores > 0:
        logger.info(f"n_invalid_scores: {n_invalid_scores}")
        logger.info(f"Using participants only with valid scores")
        df = df[df[name].isin(range(min_val, max_val+1))]

    return df
    
def format_baseline_scores(df, stratification, raw_score_name):
    """ Format baseline score sheet so it can be filtered in pandas
    """
    baselines_ranges = {}
    strata_cols = list(stratification.keys()) + [raw_score_name]

    for col in strata_cols: 
        # No need to parse categrical columns
        if (stratification[col]["dtype"].lower() == "continuous"):
            # check if column has ranges separate by "-" delimiter
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

def get_normed_score(participant, baseline_df, stratification, raw_score_name, logger,
                     norming_procedure="lookup_scaled_score", regress_model_dict=None):
    """ Filter baseline scores and return match for a given participant
    """
    # Using regression formula directly 
    if baseline_df is None:
        if norming_procedure.lower() in ["regress", "regression"]:
            if regress_model_dict == None:
                logger.error("regress_model_dict with covariate coefficients not provided")
                normed_score = np.nan
                note = "Missing regression model coefficients"

            else:
                participant_dict = {"raw_score":participant[raw_score_name]}
                regress_covars = []
                for var_name in list(stratification.keys()):
                    participant_dict[var_name] = participant.loc[var_name]
                    if var_name != raw_score_name:
                        regress_covars.append(var_name)
                                    
                normed_score = regress(participant_dict, regress_covars, regress_model_dict)
                note = "Using regression formula"
        else:
            logger.error(f"Unknown norming procedure: {norming_procedure}")
            normed_score = np.nan
            note = "Unknown norming procedure"

    # Using stratified matching
    else:
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
            logger.info(f"Multiple matches found for participant: {participant.name}, {dict(participant)}")
            logger.info(f"Not assigning a scaled score for {participant.name}")
            normed_score = np.nan
            note = "Multiple strata matches found"

        else:
            # Select based on norming_procedure
            if norming_procedure.lower() in ["lookup_scaled_score","scaled_score"]:
                normed_score = baseline_match_df["Scaled_score"].values[0]
                note = "Scaled score"

            elif norming_procedure.lower() in ["zscore", "z-score", "z_score"]:
                participant_dict = {"raw_score":participant[raw_score_name],
                                    "Mean":baseline_match_df["Mean"].values[0],
                                    "SD":baseline_match_df["SD"].values[0]}

                normed_score = z_score(participant_dict)
                note = "zscore"

            else:
                logger.error(f"Unknown norming procedure")
                normed_score = np.nan
                note = "Unknown norming procedure"

    return normed_score, note

def z_score(participant):
    """ Calculates z-score based on mean and SD values provided
    """
    raw_score = participant["raw_score"]
    mean = participant["Mean"]
    SD = participant["SD"]
    z_score = (raw_score - mean)/SD
    return z_score

def regress(participant, regress_covars, regress_model_dict):
    """ Calculates residuals as normed scores based on a given regression model
    """
    intercept = regress_model_dict["intercept"]
    slope = regress_model_dict["slope"]
    log_scale = regress_model_dict["log_scale"]

    raw_score = participant["raw_score"]
    
    # Calculate weighted contribution of the stratification covarates
    # e.g. edu_coef*education + sex_coef*sex + age_coef*age
    weighted_covariate_sum = 0
    for var_name in regress_covars: 
        coef = regress_model_dict[var_name]
        var_value = participant[var_name]
        weighted_var = coef*var_value
        weighted_covariate_sum = weighted_covariate_sum + weighted_var

    # Based on Rebekah's (Neuropsy team) formula
    if log_scale:
        raw_score = np.log10(raw_score)
    
    normed_score = (raw_score - (weighted_covariate_sum + intercept))/slope

    return normed_score

### TMT regression models ###
# "hidden_variable_A = 3*((TMT A time seconds (Raw score) - 38.359) / 12.836) + 10",
# "hidden_variable_B = 3*((TMT B time (seconds) (Raw score) - 88.014369) / 39.157) + 10",
# "hidden_variable_AB = (3*(((Hidden_variable_2-Hidden_variable_1)--0.00000008301)/2.729) + 10) * -1",
# "TMT A-B contrast (Z-score)= =(Hidden_variable_3-(-12.475+(0.007*Age)+(0.131*Education)+(-0.049*Sex)))/2.9712"

def get_contrast_normed_score(participant, stratification, raw_score_A_name, raw_score_B_name, regress_model_dict):
    """ Calculates contrast normed scores based on hidden variables and a given regression model
    """
    # Calculate contrast score (A - B)
    raw_score_A = participant[raw_score_A_name]
    raw_score_B = participant[raw_score_B_name]

    HV_A_coef = regress_model_dict["hidden_var_A"]
    HV_B_coef = regress_model_dict["hidden_var_B"]
    HV_AB_coef = regress_model_dict["hidden_var_AB"]

    HV_A = HV_A_coef["mult_1"] * ((raw_score_A - HV_A_coef["offset_1"])/HV_A_coef["div_1"]) + HV_A_coef["offset_2"]
    HV_B = HV_B_coef["mult_1"] * ((raw_score_B - HV_B_coef["offset_1"])/HV_B_coef["div_1"]) + HV_B_coef["offset_2"]

    HV_AB = ( HV_AB_coef["mult_1"] * (((HV_B - HV_A) - HV_AB_coef["offset_1"])/HV_AB_coef["div_1"]) 
             + HV_AB_coef["offset_2"] ) * HV_AB_coef["mult_2"]
    
    HV_scores = {"hidden_var_A":HV_A, "hidden_var_B":HV_B, "hidden_var_AB": HV_AB}
    # Generate participant dict for final regression model based on HV_AB as raw score
    participant_dict = {}
    participant_dict["raw_score"] = HV_AB
    regress_covars = []
    for var_name in list(stratification.keys()):
        participant_dict[var_name] = participant.loc[var_name]
        if not var_name in [raw_score_A_name,raw_score_B_name]:
            regress_covars.append(var_name)

    # Get regression residual based on contrast score and covariates
    normed_score = regress(participant_dict, regress_covars, regress_model_dict)
    return normed_score, HV_scores