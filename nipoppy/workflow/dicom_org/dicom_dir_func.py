def participant_id_to_dicom_dir(participant_id, session_id, global_config: dict):
    DATASET_ROOT = global_config["DATASET_ROOT"]
    participant_dicom_dir_map_file = f"{DATASET_ROOT}/scratch/raw_dicom/participant_dicom_dir_map.csv"
    try:
        _df = pd.read_csv(participant_dicom_dir_map_file)
        dicom_dir = _df.loc[(_df["participant_id"]==participant_id) & 
                            (_df["session"] == session)]["participant_dicom_dir"].values[0]
    except Exception as e:
        print(f"Could not resolve participant dicom dir for participant_id: {participant_id}")
        print(e)
    return dicom_dir
