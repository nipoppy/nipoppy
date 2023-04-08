import pandas as pd
import numpy as np
import glob
import os
import workflow.logger as my_logger
from pathlib import Path
import shutil
import pydicom

def search_dicoms(raw_dicom_dir, logger, check_validity=True):
    """ Search and return list of dicom files from a scanner dicom-dir-tree output
    """
    filelist = []
    invalid_dicom_list = []
    for root, dirs, files in os.walk(raw_dicom_dir):
        for file in files:
            filepath = os.path.join(root,file)

            if check_validity: #Slow because of pydicom reads
                valid_dicom = check_valid_dicom(filepath,logger)
                if valid_dicom:
                    filelist.append(filepath)
                else:
                    invalid_dicom_list.append(filepath)
            else:
                filelist.append(filepath)

    n_dcms = len(filelist)
    unique_dcm = set(filelist)
    n_unique_dcm = len(unique_dcm)

    if n_unique_dcm != n_dcms:
        n_duplicates = n_dcms - n_unique_dcm
        logger.info(f"Duplicate dicom names found for {n_duplicates} dcms")

    return unique_dcm, invalid_dicom_list

def copy_dicoms(filelist, dicom_dir, logger, symlink=False):
    """ Copy dicoms from a scanner dicom-dir-tree output into a flat participant-level dir
    """
    if not Path(dicom_dir).is_dir():
        os.mkdir(dicom_dir)
        for f in filelist:
            f_basename = os.path.basename(f)
            if symlink:
                os.symlink(f, f"{dicom_dir}{f_basename}")
            else:
                shutil.copyfile(f, f"{dicom_dir}{f_basename}")
    else:
        logger.info(f"participant dicoms already exist")

def check_valid_dicom(f_dcm, logger):
    """ checks if the file is vaild dicom
    """
    status = False
    try:
        dcm_info = pydicom.dcmread(f_dcm)
        img_type = dcm_info[("0008", "0008")].value[0]
        if img_type == "DERIVED":
            status = False #Heudiconv cannot convert derived images
            logger.warning(f"Derived dcm: {f_dcm}")     
        else:
            status = True
    except:
        logger.warning(f"Error reading {f_dcm}")        

    return status