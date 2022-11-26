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

global_config = args.global_config
stage = args.stage
participant_id = args.participant_id
session_id = args.session_id
test_run = str(int(args.test_run))

print(f"test run: {test_run}")
# Read global configs
f = open(global_config)
json_data = json.load(f)

DATASET_ROOT = json_data["DATASET_ROOT"]
DATASTORE_DIR = json_data["DATASTORE_DIR"]
HEUDICONV_VERSION = json_data["HEUDICONV_VERSION"]
SINGULARITY_PATH = json_data["SINGULARITY_PATH"]

SINGULARITY_HEUDICONV = json_data["SINGULARITY_HEUDICONV"]
SINGULARITY_HEUDICONV = SINGULARITY_HEUDICONV.format(f"{HEUDICONV_VERSION}")

print(f"Using DATASET_ROOT: {DATASET_ROOT}")
print(f"Processing participant: {participant_id}")
print(f"Using SINGULARITY_HEUDICONV version: {SINGULARITY_HEUDICONV}")
print(f"Running HeuDiConv stage: {stage}")

# Check if dicom_dir exists for the participant
if test_run == "1":
    participant_subdir_path = f"{DATASET_ROOT}/test_data/dicom/{participant_id}"
else:
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
    
    print(HEUDICONV_CMD)
    heudiconv_proc = subprocess.run(HEUDICONV_CMD)
else: 
    print(f"{participant_subdir_path} does not exist")
