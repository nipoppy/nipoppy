from pathlib import Path

from nipoppy.trackers.tracker import SUCCESS, FAIL

# Globals
FIRST_LEVEL_DIRS = ["label", "mri", "stats", "surf"]
HEMISPHERES = ["lh","rh"]
DEFAULT_PARCELS = ["aparc","aparc.a2009s"]
ALL_PARCELS = ["aparc","aparc.a2009s","aparc.DKTatlas"]
SURF_MEASURES = ["curv","area","thickness","volume","sulc","midthickness"]

def check_fsdirs(subject_dir):
    filepath_status = True
    for fsdir in FIRST_LEVEL_DIRS:
        dirpath = Path(f"{subject_dir}/{fsdir}")
        dirpath_status = Path.is_dir(dirpath)
        if not dirpath_status:
            break
    return filepath_status

def check_mri(subject_dir):
    filepath_status = True
    for parc in DEFAULT_PARCELS:
        filepath = Path(f"{subject_dir}/mri/{parc}+aseg.mgz")
        filepath_status = Path.is_file(filepath)
        if not filepath_status:
            break
    return filepath_status

def check_label(subject_dir):
    filepath_status = True
    for parc in DEFAULT_PARCELS:
        if filepath_status:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/label/{hemi}.{parc}.annot")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    break
        else:
            break
    return filepath_status

def check_surf(subject_dir):
    filepath_status = True
    for measure in SURF_MEASURES:
        if filepath_status:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/surf/{hemi}.{measure}")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    break
        else:
            break
            
    return filepath_status

def check_stats(subject_dir, PARCELS=DEFAULT_PARCELS):
    filepath_status = True
    for parc in PARCELS:
        if filepath_status:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/stats/{hemi}.{parc}.stats")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    break
        else:
            break

    # check aseg
    filepath = Path(f"{subject_dir}/stats/aseg.stats")
    aseg_status = Path.is_file(filepath)

    return filepath_status & aseg_status

def check_run_status(subject_dir, session_id=None, run_id=None, acq_label=None):
    check_list = [check_fsdirs,check_mri,check_label,check_surf,check_stats]
    status_list = []
    for cl in check_list:
        status_list.append(cl(subject_dir))
    
    if all(status_list):
        status_msg = SUCCESS
    else:
        status_msg = FAIL
    return status_msg

def check_parcels(subject_dir, session_id=None, run_id=None, acq_label=None):
    stats_status = check_stats(subject_dir,ALL_PARCELS)
    if stats_status:
        status_msg = SUCCESS
    else:
        status_msg = FAIL
    return status_msg


tracker_configs = {
    "pipeline_complete": check_run_status,
    
    "PHASE__": {
        "parcellations": check_parcels
    }
}