import os
from pathlib import Path
import argparse
import json
import pandas as pd
import shutil
import numpy as np
from glob import glob
from joblib import Parallel, delayed
import nipoppy.workflow.logger as my_logger
# from nipoppy.workflow.tabular import generate_manifest
from nipoppy.workflow.dicom_org import run_dicom_org
from nipoppy.workflow.dicom_org import check_dicom_status
from nipoppy.workflow.bids_conv import run_bids_conv
from nipoppy.workflow.proc_pipe.mriqc import run_mriqc
from nipoppy.workflow.proc_pipe.fmriprep import run_fmriprep
from nipoppy.workflow.catalog import get_new_proc_participants
from nipoppy.workflow.catalog import generate_pybids_index
from nipoppy.trackers import run_tracker

# argparse
HELPTEXT = """
Top level script to orchestrate workflows as specified in the global_config.json
"""
parser = argparse.ArgumentParser(description=HELPTEXT)
parser.add_argument('--global_config', type=str, required=True, help='path to global config file for your nipoppy dataset')
parser.add_argument('--session_id', type=str, required=True, help='current session or visit ID for the dataset')
parser.add_argument('--n_jobs', type=int, default=4, help='number of parallel processes')

args = parser.parse_args()

# read global configs
global_config_file = args.global_config
with open(global_config_file, 'r') as f:
    global_configs = json.load(f)

DATASET_ROOT = global_configs["DATASET_ROOT"]
log_dir = f"{DATASET_ROOT}/scratch/logs/"
log_file = f"{log_dir}/nipoppy.log"

# Used to run trackers to identify new participants to process
dash_schema_file = f"{DATASET_ROOT}/proc/bagel_schema.json" 

# bids_db_path
# TODO create a common BIDS_DB for mriqc and fmriprep once relative_paths issue is resolved
FMRIPREP_VERSION = global_configs["PROC_PIPELINES"]["fmriprep"]["VERSION"]
output_dir = f"{DATASET_ROOT}/derivatives/"
fmriprep_dir = f"{output_dir}/fmriprep/v{FMRIPREP_VERSION}"
# bids_db_path = f"{fmriprep_dir}/first_run/bids_db/"

session_id = args.session_id
session = f"ses-{session_id}"

n_jobs = args.n_jobs
MAX_BATCH = 10 # Max number of participants to run BEFORE cleaning up intermediate files

logger = my_logger.get_logger(log_file, level="INFO")

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
        # generate_manifest.run(global_configs, task="regenerate", dash_bagel=True, logger=logger)
        check_dicom_status.run(global_config_file, regenerate=True, empty=False)

    elif wf == "dicom_org":        
        run_dicom_org.run(global_configs, session_id, n_jobs=n_jobs, logger=logger)

    elif wf == "bids_conv": 
        run_bids_conv.run(global_configs, session_id, n_jobs=n_jobs, logger=logger)

    elif wf == "mriqc":
        # Supported modalities (i.e. suffixes) for MRIQC
        modalities = ["T1w", "T2w"]
        ignore_patterns = ["/anat/{}_{}_acq-NM_{}","/anat/{}_{}_{}_FLAIR",
                           "/fmap/",
                           "/swi/",
                           "/perf"]

        # Run mriqc tracker to regenerate bagel
        run_tracker.run(global_configs, dash_schema_file, ["mriqc"], logger=logger)

        proc_participants, _ = get_new_proc_participants(global_configs, session_id, pipeline="mriqc", logger=logger)
        n_proc_participants = len(proc_participants)        

        if n_proc_participants > 0:
            logger.info(f"Running MRIQC on {n_proc_participants} participants from session: {session} and for modalities: {modalities}")
            # The default bids_db_path is proc/bids_db_{pipeline}
            bids_db_path = generate_pybids_index(global_configs, session_id, pipeline="mriqc", 
                                                 ignore_patterns=ignore_patterns, logger=logger)
            logger.info(f"bids_db_path: {bids_db_path}")
            # bids_db_path = None

            if n_jobs > 1:
                # Process in parallel! (Won't write to logs)
                mriqc_results = Parallel(n_jobs=n_jobs)(delayed(run_mriqc.run)(
                    global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                    modalities=modalities, output_dir=None, logger=logger) 
                    for participant_id in proc_participants)

            else:
                # Useful for debugging
                mriqc_results = []
                for participant_id in proc_participants:
                    res = run_mriqc.run(global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                                        modalities=modalities, output_dir=None, logger=logger) 
                mriqc_results.append(res)   
            
            # Rerun tracker for updated bagel
            run_tracker.run(global_configs, dash_schema_file, ["mriqc"], logger=logger)

        else:
            logger.info(f"No new participants to run MRIQC on for session: {session}") 

    elif wf == "fmriprep":
        ignore_patterns = ["/anat/{}_{}_{}_NM","/anat/{}_{}_{}_echo",
                           "/dwi/"
                           "/swi/",
                           "/perf"]
         # Run fmriprep tracker to regenerate bagel
        run_tracker.run(global_configs, dash_schema_file, ["fmriprep"], logger=logger)

        proc_participants, _ = get_new_proc_participants(global_configs, session_id, pipeline="fmriprep", logger=logger)
        n_proc_participants = len(proc_participants)
        
        if n_proc_participants > 0:
            # remove old bids_db
            sql_db_file = f"{DATASET_ROOT}/proc/bids_db_fmriprep/bids_db.sqlite" 
            logger.info(f"Removing old bids_db from {sql_db_file}")
            if os.path.exists(sql_db_file):
                os.remove(sql_db_file)

            logger.info(f"Running fmriprep on {n_proc_participants} participants from session: {session} and for modalities: {modalities}")
            # The default bids_db_path is proc/bids_db_{pipeline}
            bids_db_path = generate_pybids_index(global_configs, session_id, pipeline="fmriprep", 
                                                    ignore_patterns=ignore_patterns, logger=logger)
            logger.info(f"bids_db_path: {bids_db_path}")

            # Don't run more than MAX_BATCH participants in parallel
            # Also clean-up after MAX_BATCH participants to avoid storage issues
            if n_proc_participants > MAX_BATCH: 
                n_batches = int(np.ceil(n_proc_participants/MAX_BATCH))
                logger.info(f"Running fmriprep in {n_batches} batches of at most {MAX_BATCH} participants each")
                proc_participant_batches = np.array_split(proc_participants, n_batches)

            else:
                proc_participant_batches = [proc_participants]

            for proc_participant_batch in proc_participant_batches:
                proc_participant_batch = list(proc_participant_batch)
                logger.info(f"Running fmriprep on participants: {proc_participant_batch}")
                if n_jobs > 1:
                    # Process in parallel! (Won't write to logs)
                    fmiprep_results = Parallel(n_jobs=n_jobs)(delayed(run_fmriprep.run)(
                        global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                        output_dir=None, anat_only=False, use_bids_filter=True, logger=logger) 
                        for participant_id in proc_participant_batch)

                else:
                    # Useful for debugging
                    fmiprep_results = []
                    for participant_id in proc_participant_batch:
                        res = run_fmriprep.run(global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                                            output_dir=None, anat_only=False, use_bids_filter=True, logger=logger) 
                    fmiprep_results.append(res)   
                
                # Clean up intermediate files
                logger.info(f"Cleaning up intermediate files from {fmriprep_dir}")
                fmriprep_wf_dir = glob(f"{fmriprep_dir}/fmriprep*wf")
                subject_home_dirs = glob(f"{fmriprep_dir}/output/fmriprep_home_sub-*")
                run_toml_dirs = glob(f"{fmriprep_dir}/2023*")

                logger.info(f"fmriprep_wf_dir:\n{fmriprep_wf_dir}")
                logger.info(f"subject_home_dirs:\n{subject_home_dirs}")
                logger.info(f"run_toml_dirs:\n{run_toml_dirs}")

                for cleanup_dir in fmriprep_wf_dir + subject_home_dirs + run_toml_dirs:
                    shutil.rmtree(cleanup_dir)

            # Rerun tracker for updated bagel
            run_tracker.run(global_configs, dash_schema_file, ["fmriprep"], logger=logger)
            
    else:
        logger.error(f"Unknown workflow: {wf}")

    logger.info("-"*50)
    logger.info(f"Finishing workflow: {wf}")
    logger.info("-"*50)

logger.info("-"*75)
logger.info(f"Finishing nipoppy run...")
logger.info("-"*75)