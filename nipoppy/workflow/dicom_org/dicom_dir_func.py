import pandas as pd
def participant_id_to_dicom_dir(participant_id, session_id, global_config: dict):
    """ Looks up participant's dicom_dir based on participant_id. If not found the assumes identical dicom_dir name.
    """
    DATASET_ROOT = global_config["DATASET_ROOT"]
    session = f"ses-{session_id}"
    participant_dicom_dir_map_file = f"{DATASET_ROOT}/scratch/raw_dicom/participant_dicom_dir_map.csv"
    try:
        _df = pd.read_csv(participant_dicom_dir_map_file)
        dicom_dir = _df.loc[(_df["participant_id"]==participant_id) & 
                            (_df["session"] == session)]["participant_dicom_dir"].values[0]
        if pd.isna(dicom_dir):
            dicom_dir = str(participant_id)

    except Exception as e:
        print(f"Could not resolve participant dicom dir for participant_id: {participant_id}")
        print(e)
        dicom_dir = str(participant_id)
    return dicom_dir
