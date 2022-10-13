import argparse
import json
import subprocess

HELPTEXT = """
Script to perform DICOM to BIDS conversion using HeuDiConv
"""
#Author: nikhil153
#Date: 07-Oct-2022

# argparse
parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--stage', type=int, help='participant id')
parser.add_argument('--participant_id', type=str, help='heudiconv stage (either 1 or 2)')
parser.add_argument('--session_id', type=str, help='session id for the participant')
parser.add_argument('--test_run', default=False, action=argparse.BooleanOptionalAction, help='do a test run or not')

args = parser.parse_args()

global_config = args.global_config
stage = args.stage
participant_id = args.participant_id
session_id = args.session_id
test_run = str(int(args.test_run))
  
# Read global configs
f = open(global_config)
json_data = json.load(f)

DATASET_ROOT = json_data["DATASET_ROOT"]
DATASTORE_DIR = json_data["DATASTORE_DIR"]
HEUDICONV_VERSION = json_data["HEUDICONV_VERSION"]
SINGULARITY_PATH = json_data["SINGULARITY_PATH"]

SINGULARITY_HEUDICONV = json_data["SINGULARITY_HEUDICONV"]
SINGULARITY_HEUDICONV = SINGULARITY_HEUDICONV.format(HEUDICONV_VERSION)

print(f"Using DATASET_ROOT: {DATASET_ROOT}")
print(f"Using SINGULARITY_HEUDICONV: {SINGULARITY_HEUDICONV}")
print(f"Running HeuDiConv stage: {stage}")

# Run HeuDiConv script
# /heudiconv_run1.sh -d <dataset_root> -p <MNI01> -s <01> -l <./> -t 1
HEUDICONV_SCRIPT = f"scripts/heudiconv_stage_{stage}.sh"
HEUDICONV_ARGS = ["-d", DATASET_ROOT, "-i", SINGULARITY_HEUDICONV, "-r", SINGULARITY_PATH, \
                  "-p", participant_id, "-s", session_id, "-l", DATASTORE_DIR, "-t", test_run]
HEUDICONV_CMD = [HEUDICONV_SCRIPT] + HEUDICONV_ARGS

heudiconv_proc = subprocess.run(HEUDICONV_CMD)
