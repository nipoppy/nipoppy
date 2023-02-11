from pathlib import Path


# Globals
FIRST_LEVEL_DIRS = ["label", "mri", "stats", "surf"]
HEMISPHERES = ["lh","rh"]
PARCELS = ["aparc","aparc.a2009s","aparc.DKTatlas"]
SURF_MEASURES = ["curv","area","thickness","volume","sulc","midthickness"]

# Status flags
SUCCESS="SUCCESS"
FAIL="FAIL"
INCOMPLETE="INCOMPLETE"
UNAVAILABLE="UNAVAILABLE"

def check_fsdirs(subject_dir):
    status_msg = SUCCESS
    for fsdir in FIRST_LEVEL_DIRS:
        dirpath = Path(f"{subject_dir}/{fsdir}")
        dirpath_status = Path.is_dir(dirpath)
        if not dirpath_status:
            status_msg = FAIL
            break
    return status_msg

def check_mri(subject_dir):
    status_msg = SUCCESS
    for parc in PARCELS:
        filepath = Path(f"{subject_dir}/mri/{parc}+aseg.mgz")
        filepath_status = Path.is_file(filepath)
        if not filepath_status:
            status_msg = FAIL
            break
    return status_msg

def check_label(subject_dir):
    status_msg = SUCCESS
    for parc in PARCELS:
        if status_msg == SUCCESS:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/label/{hemi}.{parc}.annot")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    status_msg = FAIL
                    break
        else:
            break
    return status_msg

def check_stats(subject_dir):
    status_msg = SUCCESS
    for parc in PARCELS:
        if status_msg == SUCCESS:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/stats/{hemi}.{parc}.stats")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    status_msg = FAIL
                    break
        else:
            break

    # check aseg
    filepath = Path(f"{subject_dir}/stats/aseg.stats")
    filepath_status = Path.is_file(filepath)
    if not filepath_status:
        status_msg = FAIL

    return status_msg

def check_surf(subject_dir):
    status_msg = SUCCESS
    for measure in SURF_MEASURES:
        if status_msg == SUCCESS:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/surf/{hemi}.{measure}")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    status_msg = FAIL
                    break
        else:
            break
            
    return status_msg

def check_run_status(subject_dir):
    fsdir_status = check_fsdirs(subject_dir)
    stats_status = check_stats(subject_dir)
    if (fsdir_status==SUCCESS) & (stats_status==SUCCESS):
        status_msg = SUCCESS
    else:
        status_msg = FAIL
    return status_msg

tracker_configs = {
    "pipeline_complete": check_run_status,
    
    "Phase_": {
            "DKT": check_stats
            }
}