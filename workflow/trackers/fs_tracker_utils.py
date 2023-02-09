from re import ASCII
import pandas as pd
from pathlib import Path
import argparse
import glob
import os

# Globals
FIRST_LEVEL_DIRS = ["label", "mri", "stats", "surf"]
HEMISPHERES = ["lh","rh"]
PARCELS = ["aparc","aparc.a2009s","aparc.DKTatlas"]
SURF_MEASURES = ["curv","area","thickness","volume","sulc","midthickness"]

PASS_STATUS = True
FAIL_STATUS = False

def check_fsdirs(subject_dir):
    status_msg = PASS_STATUS
    for fsdir in FIRST_LEVEL_DIRS:
        dirpath = Path(f"{subject_dir}/{fsdir}")
        dirpath_status = Path.is_dir(dirpath)
        if not dirpath_status:
            status_msg = FAIL_STATUS
            break
    return status_msg

def check_mri(subject_dir):
    status_msg = PASS_STATUS
    for parc in PARCELS:
        filepath = Path(f"{subject_dir}/mri/{parc}+aseg.mgz")
        filepath_status = Path.is_file(filepath)
        if not filepath_status:
            status_msg = FAIL_STATUS
            break
    return status_msg

def check_label(subject_dir):
    status_msg = PASS_STATUS
    for parc in PARCELS:
        if status_msg == PASS_STATUS:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/label/{hemi}.{parc}.annot")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    status_msg = FAIL_STATUS
                    break
        else:
            break
    return status_msg

def check_stats(subject_dir):
    status_msg = PASS_STATUS
    for parc in PARCELS:
        if status_msg == PASS_STATUS:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/stats/{hemi}.{parc}.stats")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    status_msg = FAIL_STATUS
                    break
        else:
            break

    # check aseg
    filepath = Path(f"{subject_dir}/stats/aseg.stats")
    filepath_status = Path.is_file(filepath)
    if not filepath_status:
        status_msg = FAIL_STATUS

    return status_msg

def check_surf(subject_dir):
    status_msg = PASS_STATUS
    for measure in SURF_MEASURES:
        if status_msg == PASS_STATUS:
            for hemi in HEMISPHERES:
                filepath = Path(f"{subject_dir}/surf/{hemi}.{measure}")
                filepath_status = Path.is_file(filepath)
                if not filepath_status:
                    status_msg = FAIL_STATUS
                    break
        else:
            break
            
    return status_msg

def check_run_status(subject_dir):
    fsdir_status = check_fsdirs(subject_dir)
    stats_status = check_stats(subject_dir)
    status_msg = fsdir_status & stats_status
    return status_msg

tracker_configs = {
    "Global_": {
        "run_status": check_run_status
    },
    "Phase_": {
        "DKT_stats": check_stats
    },
}