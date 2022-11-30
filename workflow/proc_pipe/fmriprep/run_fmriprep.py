import argparse
import json
import subprocess
import os
from pathlib import Path
import shutil

#Author: nikhil153
#Date: 07-Oct-2022

# argparse
HELPTEXT = """
Script to run fMRIPrep 
"""

parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--participant_id', type=str, help='participant id')
parser.add_argument('--session_id', type=str, help='session id for the participant')
parser.add_argument('--output_dir', type=str, help='specify custom output dir (default: <DATASET_ROOT>/derivatives)')
parser.add_argument('--use_bids_filter', action='store_true', help='use bids filter or not')
parser.add_argument('--anat_only', action='store_true', help='run only anatomical workflow or not')
parser.add_argument('--test_run', action='store_true', help='do a test run or not')

args = parser.parse_args()

global_config = args.global_config
participant_id = args.participant_id
session_id = args.session_id
output_dir = args.output_dir # Needed on BIC (QPN) due to weird permissions issues with mkdir
use_bids_filter = args.use_bids_filter
bids_filter = str(int(use_bids_filter)) #reformat for shell script argument
anat_only = str(int(args.anat_only))
test_run = str(int(args.test_run))

  
# Read global configs
f = open(global_config)
json_data = json.load(f)

DATASET_ROOT = json_data["DATASET_ROOT"]
SINGULARITY_PATH = json_data["SINGULARITY_PATH"]
TEMPLATEFLOW_DIR = json_data["TEMPLATEFLOW_DIR"]

FMRIPREP_VERSION = json_data["FMRIPREP_VERSION"]

SINGULARITY_FMRIPREP = json_data["SINGULARITY_FMRIPREP"]
SINGULARITY_FMRIPREP = SINGULARITY_FMRIPREP.format(FMRIPREP_VERSION)

if output_dir is None:
    output_dir = DATASET_ROOT

print(f"Using DATASET_ROOT: {DATASET_ROOT}")
print(f"Using output_dir: {output_dir}")
print(f"Using SINGULARITY_FMRIPREP: {SINGULARITY_FMRIPREP}")

# Create version specific output dir
Path(f"{output_dir}/derivatives/fmriprep/v{FMRIPREP_VERSION}").mkdir(parents=True, exist_ok=True)

fname = __file__
CWD = os.path.dirname(os.path.abspath(fname))
print(f"CWD: {CWD}, fname: {fname}")

#Copy bids_filter.json `<DATASET_ROOT>/bids/bids_filter.json`
if use_bids_filter:
    print(f"Copying ./bids_filter.json to {DATASET_ROOT}/bids/bids_filter.json (to be seen by Singularity container)")
    if test_run == "1":
        shutil.copyfile(f"{CWD}/bids_filter.json", f"{DATASET_ROOT}/test_data/bids/bids_filter.json")
    else:
        shutil.copyfile(f"{CWD}/bids_filter.json", f"{DATASET_ROOT}/bids/bids_filter.json")

# Run FMRIPREP script
# "Sample cmd: ./run_fmriprep_anat_and_func.sh -d <dataset_root> -i <path_to_fmriprep_img> -r <singularity> \
#         -f <path_to_templateflow_dir> -p <MNI01> -s <01> -b 1 -a 1 -t 1"

FMRIPREP_SCRIPT = f"{CWD}/scripts/run_fmriprep.sh"
FMRIPREP_ARGS = ["-d", DATASET_ROOT, "-o", output_dir, "-i", SINGULARITY_FMRIPREP, "-r", SINGULARITY_PATH, \
                 "-f", TEMPLATEFLOW_DIR, "-p", participant_id, "-s", session_id, "-b", bids_filter, \
                 "-a", anat_only, "-v", f"v{FMRIPREP_VERSION}", "-t", test_run]
FMRIPREP_CMD = [FMRIPREP_SCRIPT] + FMRIPREP_ARGS

fmriprep_proc = subprocess.run(FMRIPREP_CMD)
