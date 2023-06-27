import os
import logging
from pathlib import Path
import shutil
import pydicom

# logger
LOG_FILE = "../mr_proc.log"
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)

# Use FileHandler() to log to a file
file_handler = logging.FileHandler(LOG_FILE, mode="a")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)

# Don't forget to add the file handler
logger.addHandler(file_handler)

def search_dicoms(raw_dicom_dir, skip_dcm_check=False):
    """ Search and return list of dicom files from a scanner dicom-dir-tree output
    """
    filelist = []
    invalid_dicom_list = []
    for root, dirs, files in os.walk(raw_dicom_dir):
        for file in files:
            filepath = os.path.join(root,file)
            if skip_dcm_check:
                valid_dicom = check_valid_dicom(filepath)
                if valid_dicom:
                    filelist.append(filepath)
                else:
                    invalid_dicom_list.append(filepath)
    
    n_dcms = len(filelist)
    unique_dcm = set(filelist)
    n_unique_dcm = len(unique_dcm)

    if n_unique_dcm != n_dcms:
        n_duplicates = n_dcms - n_unique_dcm
        logger.debug(f"Duplicate dicom names found for {n_duplicates} dcms")

    return unique_dcm, invalid_dicom_list

def copy_dicoms(filelist, dicom_dir, symlink=False):
    """ Copy dicoms from a scanner dicom-dir-tree output into a flat participant-level dir
    """
    if not Path(dicom_dir).is_dir():
        os.mkdir(dicom_dir)
        for f in filelist:
            f_basename = os.path.basename(f)
            fpath_dest = Path(f"{dicom_dir}{f_basename}")
            if symlink:
                f = os.path.relpath(f, fpath_dest.parent)
                os.symlink(f, fpath_dest)
            else:
                shutil.copyfile(f, fpath_dest)
    else:
        logger.debug(f"participant dicoms already exist")

def check_valid_dicom(f_dcm):
    """ checks if the file is valid dicom
    """
    status = False
    try:
        dcm_info = pydicom.dcmread(f_dcm)
        img_type = dcm_info[("0008", "0008")].value[0]
        if img_type == "DERIVED":
            status = False #Heudiconv cannot convert derived images
        else:
            status = True
    except:
        logger.debug(f"Error reading {f_dcm}")        

    return status