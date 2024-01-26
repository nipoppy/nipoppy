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
from nipoppy.workflow import make_doughnut
from nipoppy.workflow.bids_conv import run_bids_conv
from nipoppy.workflow.proc_pipe.mriqc import run_mriqc
from nipoppy.workflow.proc_pipe.fmriprep import run_fmriprep
from nipoppy.workflow.catalog import get_new_proc_participants
from nipoppy.workflow.catalog import generate_pybids_index
from nipoppy.trackers import run_tracker

# helper functions
def get_proc_batches(proc_participants, MAX_BATCH, logger):
    """ Generates MAX_BATCH participants to run at any given time before clean-up
    """
    n_proc_participants = len(proc_participants)
    if n_proc_participants > MAX_BATCH: 
        n_batches = int(np.ceil(n_proc_participants/MAX_BATCH))
        logger.info(f"Running fmriprep in {n_batches} batches of at most {MAX_BATCH} participants each")
        proc_participant_batches = np.array_split(proc_participants, n_batches)
    else:
        proc_participant_batches = [proc_participants]    

    return proc_participant_batches

def refresh_bids_db(global_configs, session_id, pipeline, ignore_patterns, logger):
    """ Remove and rebuilds the bids_db for the given pipeline with the given ignore_patterns
    """
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    # remove old bids_db
    sql_db_file = f"{DATASET_ROOT}/proc/bids_db_{pipeline}/bids_db.sqlite" 
    logger.info(f"Removing old bids_db from {sql_db_file}")
    if os.path.exists(sql_db_file):
        os.remove(sql_db_file)

    # The default bids_db_path is proc/bids_db_{pipeline}
    bids_db_path = generate_pybids_index(global_configs, session_id, pipeline=pipeline, 
                                         ignore_patterns=ignore_patterns, logger=logger)
    logger.info(f"bids_db_path: {bids_db_path}")
    
    return bids_db_path

# argparse
HELPTEXT = """
Top level script to orchestrate workflows as specified in the global_config.json
"""
parser = argparse.ArgumentParser(description=HELPTEXT)
parser.add_argument('--global_config', type=str, required=True, help='path to global config file for your nipoppy dataset')
parser.add_argument('--session_id', type=str, required=True, help='current session or visit ID for the dataset')
parser.add_argument('--workflows', type=str, nargs="*", help='workflows to run in order (default: all))')
parser.add_argument('--use_hpc', action='store_true', help='dispatch proc_pipe jobs to HPC (default: False)')
parser.add_argument('--n_jobs', type=int, default=4, help='number of parallel processes')
parser.add_argument('--n_max_cleanup', type=int, default=10, help='number of participants to run before cleaning up intermediate files')

args = parser.parse_args()

# read global configs
global_config_file = args.global_config
with open(global_config_file, 'r') as f:
    global_configs = json.load(f)

DATASET_ROOT = global_configs["DATASET_ROOT"]

log_dir = f"{DATASET_ROOT}/scratch/logs/"
log_file = f"{log_dir}/nipoppy.log"
logger = my_logger.get_logger(log_file, level="INFO")

# Used to run trackers to identify new participants to process
dash_schema_file = f"{DATASET_ROOT}/proc/bagel_schema.json" 

# bids_db_path
FMRIPREP_VERSION = global_configs["PROC_PIPELINES"]["fmriprep"]["VERSION"]
output_dir = f"{DATASET_ROOT}/derivatives/"
fmriprep_dir = f"{output_dir}/fmriprep/{FMRIPREP_VERSION}"

session_id = args.session_id
session = f"ses-{session_id}"

# HPC job list dir
hpc_job_list_dir = f"{DATASET_ROOT}/proc/"

# Number of parallel jobs to run
n_jobs = args.n_jobs
# Max number of participants to run BEFORE cleaning up intermediate files
MAX_BATCH = args.n_max_cleanup 
# Use HPC to run proc_pipe jobs
use_hpc = args.use_hpc

# Workflows to run
workflows = args.workflows
if not workflows:
    workflows = global_configs["WORKFLOWS"]

# if workflows include proc_pipes then include all proc_pipes from global config (freesurfer is not run by default)
proc_pipes = list(global_configs["PROC_PIPELINES"].keys())
if "proc_pipes" in workflows:
    logger.info(f"Running all proc_pipes: {proc_pipes}")
    workflows.remove("proc_pipes")
    workflows.extend(proc_pipes)

# Run all available trackers at the end
ALL_TRACKERS = ["heudiconv"] + proc_pipes

logger.info("-"*75)
logger.info(f"Starting nipoppy for {DATASET_ROOT} dataset...")
logger.info("-"*75)

logger.info(f"dataset session (i.e visit): {session}")
logger.info(f"Running workflows: {workflows} serially")
logger.info(f"Running {n_jobs} jobs in parallel (only for local workflows)")
logger.info(f"Cleaning up intermediate files after {MAX_BATCH} participants (only for local workflows)")
logger.info(f"Using HPC for proc pipelines: {use_hpc}")

for wf in workflows:
    logger.info("-"*50)
    logger.info(f"Starting workflow: {wf}")
    logger.info("-"*50)

    if wf == "generate_manifest":
        logger.info(f"***All sessions are fetched while generating manifest***")
        # generate_manifest.run(global_configs, task="regenerate", dash_bagel=True, logger=logger)
        logger.info(f"test run NOT generating manifest")
        make_doughnut.run(global_config_file, regenerate=True, empty=False)

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
        run_tracker.run(global_configs, dash_schema_file, [wf], session_id=session_id, logger=logger)

        proc_participants, _ = get_new_proc_participants(global_configs, session_id, pipeline=wf, logger=logger)
        n_proc_participants = len(proc_participants)        

        if n_proc_participants > 0:
            logger.info(f"Running MRIQC on {n_proc_participants} participants from session: {session} and for modalities: {modalities}")
            bids_db_path = refresh_bids_db(global_configs, session_id, wf, ignore_patterns, logger)

            # Generate a list of participants to run on HPC 
            if use_hpc:                    
                hpc_job_list_file = f"{hpc_job_list_dir}/hpc_job_list_{wf}_{session}.txt"
                logger.info(f"Generating HPC job list for {n_proc_participants} participants: {hpc_job_list_file}")
                pd.DataFrame(data=proc_participants).to_csv(hpc_job_list_file, header=False, index=False)
                
            else:
                if n_jobs > 1:
                    # Process in parallel! (Won't write to logs)
                    wf_results = Parallel(n_jobs=n_jobs)(delayed(run_mriqc.run)(
                        global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                        modalities=modalities, output_dir=None, logger=logger) 
                        for participant_id in proc_participants)

                else:
                    # Useful for debugging
                    wf_results = []
                    for participant_id in proc_participants:
                        res = run_mriqc.run(global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                                            modalities=modalities, output_dir=None, logger=logger) 
                    wf_results.append(res)   
                
        else:
            logger.info(f"No new participants to run MRIQC on for session: {session}") 

    elif wf == "fmriprep":
        ignore_patterns = ["/anat/{}_{}_{}_NM","/anat/{}_{}_{}_echo",
                           "/dwi/"
                           "/swi/",
                           "/perf"]
         # Run fmriprep tracker to regenerate bagel
        run_tracker.run(global_configs, dash_schema_file, [wf], session_id=session_id, logger=logger)

        proc_participants, _ = get_new_proc_participants(global_configs, session_id, pipeline=wf, logger=logger)
        n_proc_participants = len(proc_participants)
        
        if n_proc_participants > 0:
            bids_db_path = refresh_bids_db(global_configs, session_id, wf, ignore_patterns, logger)

            # Generate a list of participants to run on HPC 
            if use_hpc:                
                hpc_job_list_file = f"{hpc_job_list_dir}/hpc_job_list_{wf}_{session}.txt"
                logger.info(f"Generating HPC job list for {n_proc_participants} participants: {hpc_job_list_file}")
                pd.DataFrame(data=proc_participants).to_csv(hpc_job_list_file, header=False, index=False)

            else:
                proc_participant_batches = get_proc_batches(proc_participants, MAX_BATCH, logger)
                for proc_participant_batch in proc_participant_batches:
                    proc_participant_batch = list(proc_participant_batch)
                    logger.info(f"Running fmriprep on participants: {proc_participant_batch}")
                    if n_jobs > 1:
                        # Process in parallel! (Won't write to logs)
                        wf_results = Parallel(n_jobs=n_jobs)(delayed(run_fmriprep.run)(
                            global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                            output_dir=None, anat_only=False, use_bids_filter=True, logger=logger) 
                            for participant_id in proc_participant_batch)

                    else:
                        # Useful for debugging
                        wf_results = []
                        for participant_id in proc_participant_batch:
                            res = run_fmriprep.run(global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                                                output_dir=None, anat_only=False, use_bids_filter=True, logger=logger) 
                        wf_results.append(res)   
                    
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

    elif wf == "freesurfer":
        logger.info(f"freesurfer is currently run within the fmriprep run")

    elif wf == "tractoflow":
         # Run tractoflow tracker to regenerate bagel
        run_tracker.run(global_configs, dash_schema_file, [wf], session_id=session_id, logger=logger)

        proc_participants, _ = get_new_proc_participants(global_configs, session_id, pipeline=wf, logger=logger)
        n_proc_participants = len(proc_participants)
        
        if n_proc_participants > 0:
            # Generate a list of participants to run on HPC 
            if use_hpc:                
                hpc_job_list_file = f"{hpc_job_list_dir}/hpc_job_list_{wf}_{session}.txt"
                logger.info(f"Generating HPC job list for {n_proc_participants} participants: {hpc_job_list_file}")
                pd.DataFrame(data=proc_participants).to_csv(hpc_job_list_file, header=False, index=False)

            else:
                proc_participant_batches = get_proc_batches(proc_participants, MAX_BATCH, logger)
                for proc_participant_batch in proc_participant_batches:
                    proc_participant_batch = list(proc_participant_batch)
                    logger.info(f"Running fmriprep on participants: {proc_participant_batch}")
                    if n_jobs > 1:
                        # Process in parallel! (Won't write to logs)
                        wf_results = Parallel(n_jobs=n_jobs)(delayed(run_fmriprep.run)(
                            global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                            output_dir=None, anat_only=False, use_bids_filter=True, logger=logger) 
                            for participant_id in proc_participant_batch)

                    else:
                        # Useful for debugging
                        wf_results = []
                        for participant_id in proc_participant_batch:
                            res = run_fmriprep.run(global_configs=global_configs, session_id=session_id, participant_id=participant_id, 
                                                output_dir=None, anat_only=False, use_bids_filter=True, logger=logger) 
                        wf_results.append(res)   
                
    else:
        logger.error(f"Unknown workflow: {wf}")

    logger.info("-"*50)
    logger.info(f"Finishing workflow: {wf}")
    logger.info("-"*50)

# Rerun tracker(s) to update bagel
logger.info(f"Running ALL trackers: {ALL_TRACKERS} to update bagel")
run_tracker.run(global_configs, dash_schema_file, ALL_TRACKERS, session_id="ALL", logger=logger)

logger.info("-"*75)
logger.info(f"Finishing nipoppy run...")
logger.info("-"*75)