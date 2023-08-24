import os
from pathlib import Path
import argparse
import json
import pandas as pd
from joblib import Parallel, delayed
import nipoppy.workflow.logger as my_logger
# from nipoppy.workflow.tabular import generate_manifest
from nipoppy.workflow.dicom_org import run_dicom_org
from nipoppy.workflow.dicom_org import check_dicom_status
from nipoppy.workflow.bids_conv import run_bids_conv
from nipoppy.workflow.proc_pipe.mriqc import run_mriqc
from nipoppy.workflow.catalog import get_new_proc_participants
# from nipoppy.workflow.catalog import generate_pybids_index
from nipoppy.trackers import run_tracker

# argparse
HELPTEXT = """
Top level script to orchestrate workflows as specified in the global_config.json
"""
parser = argparse.ArgumentParser(description=HELPTEXT)
parser.add_argument('--global_config', type=str, required=True, help='path to global config file for your nipoppy dataset')
parser.add_argument('--session_id', type=str, required=True, help='current session or visit ID for the dataset')
parser.add_argument('--n_jobs', type=int, default=4, help='number of parallel processes')
parser.add_argument('--log_level', type=str, default="INFO", help='log level')

args = parser.parse_args()

# read global configs
global_config_file = args.global_config
with open(global_config_file, 'r') as f:
    global_configs = json.load(f)

DATASET_ROOT = global_configs["DATASET_ROOT"]
log_dir = f"{DATASET_ROOT}/scratch/logs/"
log_file = f"{log_dir}/nipoppy.log"

session_id = args.session_id
session = f"ses-{session_id}"

log_level = args.log_level.upper()

n_jobs = args.n_jobs

logger = my_logger.get_logger(log_file, level=log_level)

logger.info("-"*75)
logger.info(f"Starting nipoppy for {DATASET_ROOT} dataset...")
logger.info("-"*75)

logger.info(f"dataset session (i.e visit): {session}")
logger.info(f"Running {n_jobs} jobs in parallel")

workflows = global_configs["WORKFLOWS"]
logger.info(f"Running workflows: {workflows} serially")

for wf in workflows:
    logger.info("-"*50)
    logger.info(f"Starting workflow: {wf}")
    logger.info("-"*50)

    if wf == "generate_manifest":
        logger.info(f"***All sessions are fetched while generating manifest***")
        # dataset specific
        # generate_manifest.run(global_configs, task="regenerate", dash_bagel=True, logger=logger)
        check_dicom_status.run(global_config_file, regenerate=True, empty=False)

    elif wf == "dicom_org":        
        run_dicom_org.run(global_configs, session_id, n_jobs=n_jobs, logger=logger)

    elif wf == "bids_conv": 
        run_bids_conv.run(global_configs, session_id, n_jobs=n_jobs, logger=logger)

    elif wf == "mriqc":
        # Supported modalities (i.e. suffixes) for MRIQC
        modalities = ["T1w", "T2w"]
        
        # Run mriqc tracker to regenerate bagel
        dash_schema_file = f"{DATASET_ROOT}/proc/bagel_schema.json" 
        run_tracker.run(global_configs, dash_schema_file, ["mriqc"], logger=logger)

        proc_participants = get_new_proc_participants(global_configs, session_id, pipeline="mriqc", logger=logger)
        n_proc_participants = len(proc_participants)
        logger.info(f"Running MRIQC on {n_proc_participants} participants from session: {session} and for modalities: {modalities}")

        if n_proc_participants > 0:

            # TODO: Generate pybids index with relative paths to be accessible by singularity
            # bids_db_path = generate_pybids_index(global_configs, session_id, "mriqc", logger)
            bids_db_path = None

            if n_jobs > 1:
                # Process in parallel! (Won't write to logs)
                mriqc_results = Parallel(n_jobs=n_jobs)(delayed(run_mriqc.run)(
                    global_configs=global_configs, session_id=session_id, participant_id=participant_id, modalities=modalities, output_dir=None, logger=logger) 
                    for participant_id in proc_participants)

            else:
                # Useful for debugging
                mriqc_results = []
                for participant_id in proc_participants:
                    res = run_mriqc.run(global_configs=global_configs, session_id=session_id, participant_id=participant_id, modalities=modalities, output_dir=None, logger=logger) 
                mriqc_results.append(res)   
            
            # Rerun tracker for updated bagel
            run_tracker.run(global_configs, dash_schema_file, ["mriqc"], logger=logger)

        else:
            logger.info(f"No new participants to run MRIQC on for session: {session}") 
            
    else:
        logger.error(f"Unknown workflow: {wf}")

    logger.info("-"*50)
    logger.info(f"Finishing workflow: {wf}")
    logger.info("-"*50)

logger.info("-"*75)
logger.info(f"Finishing nipoppy run...")
logger.info("-"*75)