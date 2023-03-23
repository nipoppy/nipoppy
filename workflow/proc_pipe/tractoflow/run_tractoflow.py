import argparse
import json
import subprocess
import os
from pathlib import Path
import shutil

#Author: bcmcpher (Brent McPherson
#Date: 17-Mar-2023 (created)

# argparse
HELPTEXT = """
Script to run TractoFlow 
"""

parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--participant_id', type=str, help='participant id')
parser.add_argument('--session_id', type=str, help='session id for the participant')
parser.add_argument('--output_dir', type=str, help='specify custom output dir (default: <DATASET_ROOT>/derivatives)')
parser.add_argument('--use_bids_filter', action='store_true', help='use bids filter or not')
parser.add_argument('--test_run', action='store_true', help='do a test run or not')

args = parser.parse_args()

global_config_file = args.global_config
participant_id = args.participant_id
session_id = args.session_id
output_dir = args.output_dir # Needed on BIC (QPN) due to weird permissions issues with mkdir
use_bids_filter = args.use_bids_filter
bids_filter = str(int(use_bids_filter)) #reformat for shell script argument
test_run = args.test_run

##
## Read global configs
##

with open(global_config_file, 'r') as f:
    global_configs = json.load(f)

DATASET_ROOT = global_configs["DATASET_ROOT"]
DATASTORE_DIR = global_configs["DATASTORE_DIR"]
TEMPLATEFLOW_DIR = global_configs["TEMPLATEFLOW_DIR"]
SINGULARITY_PATH = global_configs["SINGULARITY_PATH"]
CONTAINER_STORE = global_configs["CONTAINER_STORE"]

TRACTOFLOW_CONTAINER = global_configs["PROC_PIPELINES"]["tractoflow"]["CONTAINER"]
TRACTOFLOW_VERSION = global_configs["PROC_PIPELINES"]["tractoflow"]["VERSION"]
TRACTOFLOW_CONTAINER = TRACTOFLOW_CONTAINER.format(TRACTOFLOW_VERSION)

SINGULARITY_TRACTOFLOW = f"{CONTAINER_STORE}{TRACTOFLOW_CONTAINER}"

if output_dir is None:
    output_dir = DATASET_ROOT

print(f"Using DATASET_ROOT: {DATASET_ROOT}")
print(f"Using output_dir: {output_dir}")
print(f"Using SINGULARITY_TRACTOFLOW: {SINGULARITY_TRACTOFLOW}")

# Specify paths
if test_run:
    print("Doing a test run")
    bids_dir = f"{DATASET_ROOT}/test_data/bids/"
    derivs_dir = f"{output_dir}/test_data/derivatives/"
else:
    bids_dir = f"{DATASET_ROOT}/bids/"
    derivs_dir = f"{output_dir}/derivatives/"

tractoflow_dir = f"{output_dir}/derivatives/tractoflow/v{TRACTOFLOW_VERSION}"

Path(f"{tractoflow_dir}/output").mkdir(parents=True, exist_ok=True)

fname = __file__
CWD = os.path.dirname(os.path.abspath(fname))
# print(f"CWD: {CWD}, fname: {fname}")

# Copy bids_filter.json `<DATASET_ROOT>/bids/bids_filter.json`
if use_bids_filter:
    print(f"Copying ./bids_filter.json to {DATASET_ROOT}/bids/bids_filter.json (to be seen by Singularity container)")
    shutil.copyfile(f"{CWD}/bids_filter.json", f"{bids_dir}/bids_filter.json")

## bad, old way to do it
# setup singularity run script command
# TRACTOFLOW_SCRIPT = f"{CWD}/scripts/run_fmriprep.sh"

# TRACTOFLOW_SCRIPT is this?
TRACTOFLOW_SCRIPT="nextflow run tractoflow/main.nf"

## additional arguments? how can these be extracted?
#bids_dir ## may need to be generic input directory
dti_shells = "0 1000"
fodf_shells = "0 1000"
sh_order = 6
ncore = 4

TRACTOFLOW_ARGS = ["--bids_input", bids_dir, "--dti_shells", dti_shells, "--fodf_shells", fodf_shells, "--sh_order", sh_order, "--processes", ncore, \
                   "-profile", "fully_reproducible", "-with-singularity", SINGULARITY_TRACTOFLOW ]

TRACTOFLOW_CMD = [TRACTOFLOW_SCRIPT] + TRACTOFLOW_ARGS

print(TRACTOFLOW_CMD)
#tractoflow_proc = subprocess.run(TRACTOFLOW_CMD)

