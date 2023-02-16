import argparse
import json
import subprocess
import shutil
from pathlib import Path

#Author: nikhil153
#Date: 07-Oct-2022

# argparse
HELPTEXT = """
Script to perform DICOM to BIDS conversion using HeuDiConv
"""

parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--participant_id', type=str, help='participant id')
parser.add_argument('--session_id', type=str, help='session id for the participant')
parser.add_argument('--stage', type=int, help='heudiconv stage (either 1 or 2)')
parser.add_argument('--test_run', action='store_true', help='do a test run or not')

args = parser.parse_args()

global_config_file = args.global_config
stage = args.stage
participant_id = args.participant_id
session_id = args.session_id
test_run = str(int(args.test_run))
  
# Read global configs
with open(global_config_file, 'r') as f:
    global_configs = json.load(f)

DATASET_ROOT = global_configs["DATASET_ROOT"]
DATASTORE_DIR = global_configs["DATASTORE_DIR"]
SINGULARITY_PATH = global_configs["SINGULARITY_PATH"]
CONTAINER_STORE = global_configs["CONTAINER_STORE"]

HEUDICONV_CONTAINER = global_configs["BIDS"]["heudiconv"]["CONTAINER"]
HEUDICONV_VERSION = global_configs["BIDS"]["heudiconv"]["VERSION"]
HEUDICONV_CONTAINER = HEUDICONV_CONTAINER.format(HEUDICONV_VERSION)

SINGULARITY_HEUDICONV = f"{CONTAINER_STORE}{HEUDICONV_CONTAINER}"

print(f"Using DATASET_ROOT: {DATASET_ROOT}")
print(f"Processing participant: {participant_id}")
print(f"Using SINGULARITY_HEUDICONV: {SINGULARITY_HEUDICONV}")
print(f"Running HeuDiConv stage: {stage}")

# Check if dicom_dir exists for the participant
participant_subdir_path = f"{DATASET_ROOT}/dicom/{participant_id}"
dir_status = Path(participant_subdir_path).is_dir()

if dir_status:
    # Copy heuristic.py into "DATASET_ROOT/proc/heuristic.py"
    if stage == 2:
        print(f"Copying ./heuristic.py to {DATASET_ROOT}/proc/heuristic.py (to be seen by Singularity container)")
        shutil.copyfile("heuristic.py", f"{DATASET_ROOT}/proc/heuristic.py")

    # Run HeuDiConv script
    HEUDICONV_SCRIPT = f"scripts/heudiconv_stage_{stage}.sh"
    HEUDICONV_ARGS = ["-d", DATASET_ROOT, "-i", SINGULARITY_HEUDICONV, "-r", SINGULARITY_PATH, \
                    "-p", participant_id, "-s", session_id, "-l", DATASTORE_DIR, "-t", test_run]
    HEUDICONV_CMD = [HEUDICONV_SCRIPT] + HEUDICONV_ARGS

    heudiconv_proc = subprocess.run(HEUDICONV_CMD)
else: 
    print(f"{participant_subdir_path} does not exist")