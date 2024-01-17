def participant_id_to_dicom_dir(participant_id, session_id, global_config: dict):
    dataset_root = global_config["DATASET_ROOT"]
    dicom_dir = f'{dataset_root}/scratch/raw_dicoms/ses-{session_id}/{participant_id}'
    # dicom_dir = participant_id

    return dicom_dir
