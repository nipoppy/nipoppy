import pandas as pd
from pathlib import Path
import argparse
from nipoppy.trackers.tracker import UNAVAILABLE, Tracker, get_start_time
from nipoppy.trackers import bids_tracker, fs_tracker, fmriprep_tracker, mriqc_tracker, tractoflow_tracker
import nipoppy.workflow.logger as my_logger
import json
import bids 

from nipoppy.workflow.utils import (
    BIDS_SUBJECT_PREFIX,
    BIDS_SESSION_PREFIX,
    COL_SUBJECT_MANIFEST,
    COL_BIDS_ID_MANIFEST,
    COL_SESSION_MANIFEST,
    COL_CONV_STATUS, 
    load_status,
    session_id_to_bids_session
)   

# Globals
PIPELINE_STATUS_COLUMNS = "PIPELINE_STATUS_COLUMNS"
pipeline_tracker_config_dict = {
    "heudiconv": bids_tracker.tracker_configs, 
    "freesurfer": fs_tracker.tracker_configs,
    "fmriprep": fmriprep_tracker.tracker_configs,
    "mriqc": mriqc_tracker.tracker_configs,
    "tractoflow": tractoflow_tracker.tracker_configs
}
BIDS_PIPES = ["mriqc","fmriprep", "tractoflow"]

def run(global_configs, dash_schema_file, pipelines, session_id="ALL", run_id=1, logger=None):
    """ driver code running pipeline specific trackers
    """
    DATASET_ROOT = global_configs["DATASET_ROOT"]

    # for bids tracker
    bids_dir = f"{DATASET_ROOT}/bids/"
    
    # Grab BIDS participants from the doughnut
    doughnut_file = f"{DATASET_ROOT}/scratch/raw_dicom/doughnut.csv"
    doughnut_df = load_status(doughnut_file)
    
    # logging
    log_dir = f"{DATASET_ROOT}/scratch/logs/"
    if logger is None:
        log_file = f"{log_dir}/mriqc.log"
        logger = my_logger.get_logger(log_file)

    logger.info(f"Tracking pipelines: {pipelines}")

    if session_id == "ALL":
        sessions = global_configs["SESSIONS"]
    else:
        sessions = [f"ses-{session_id}"]

    logger.info(f"tracking session_ids: {sessions}")
    
    proc_status_dfs = [] # list of dataframes
    for session in sessions:
        logger.info(f"Checking session: {session}")  
        session_id = str(session.removeprefix(BIDS_SESSION_PREFIX))
        
        for pipeline in pipelines:
            logger.info(f"Checking pipeline: {pipeline}")  
            pipe_tracker = Tracker(global_configs, dash_schema_file, pipeline) 
                
            # TODO revise tracker class
            # DATASET_ROOT, session_ids, version = pipe_tracker.get_global_configs()
            if pipeline == "heudiconv":
                version = global_configs["BIDS"][pipeline]["VERSION"]
            else:
                version = global_configs["PROC_PIPELINES"][pipeline]["VERSION"]

            schema = pipe_tracker.get_dash_schema()
            tracker_configs = pipeline_tracker_config_dict[pipeline]

            bids_participants = doughnut_df[(doughnut_df[COL_SESSION_MANIFEST]==session) & 
                                            (doughnut_df[COL_CONV_STATUS])][COL_BIDS_ID_MANIFEST].unique()
            n_bids_participants = len(bids_participants)

            logger.info("-"*50)
            logger.info(f"pipeline: {pipeline}, version: {version}")
            logger.info(f"n_participants: {n_bids_participants}, session_ids: {sessions}")
            logger.info("-"*50)

            status_check_dict = pipe_tracker.get_pipe_tasks(tracker_configs, PIPELINE_STATUS_COLUMNS, pipeline, version)

            dash_col_list = list(schema["GLOBAL_COLUMNS"].keys()) 
              
            _df = pd.DataFrame(index=bids_participants, columns=dash_col_list)          
            _df["session"] = session
            _df["pipeline_name"] = pipeline        
            _df["pipeline_version"] = version

            # BIDS (i.e. heudiconv tracker is slightly different than proc_pipes)
            if pipeline == "heudiconv":
                # Generate BIDSLayout only once per tracker run and not for each participant
                bids_layout = bids.BIDSLayout(bids_dir, validate=False)
                logger.debug(f"bids_dir: {bids_dir}")
                logger.debug(f"bids_layout: {bids_layout.get_subjects()}")
            
            for bids_id in bids_participants:
                participant_id = doughnut_df[doughnut_df[COL_BIDS_ID_MANIFEST]==bids_id][COL_SUBJECT_MANIFEST].values[0]
                _df.loc[bids_id,COL_SUBJECT_MANIFEST] = participant_id
                logger.debug(f"bids_id: {bids_id}, participant_id: {participant_id}")

                if pipeline == "heudiconv":
                    subject_dir = f"{DATASET_ROOT}/bids/{bids_id}"
                elif pipeline == "freesurfer":
                    subject_dir = f"{DATASET_ROOT}/derivatives/{pipeline}/v{version}/output/{session}/{bids_id}" 
                elif pipeline in BIDS_PIPES:
                    subject_dir = f"{DATASET_ROOT}/derivatives/{pipeline}/v{version}/output/{bids_id}" 
                else:
                    logger.error(f"unknown pipeline: {pipeline}")
                    
                dir_status = Path(subject_dir).is_dir()
                logger.debug(f"subject_dir:{subject_dir}, dir_status: {dir_status}")
                
                if dir_status:                
                    for name, func in status_check_dict.items():
                        if pipeline == "heudiconv":
                            status = func(bids_layout, participant_id, session_id, run_id)
                        else:
                            status = func(subject_dir, session_id, run_id)

                        logger.debug(f"task_name: {name}, status: {status}")
                        _df.loc[bids_id,name] = status
                        _df.loc[bids_id,"pipeline_starttime"] = get_start_time(subject_dir)
                        _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE # TODO
                else:
                    logger.warning(f"Output for pipeline: {pipeline} not found for bids_id: {bids_id}, session: {session}")
                    for name in status_check_dict.keys():                    
                        _df.loc[bids_id,name] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_starttime"] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE

            proc_status_dfs.append(_df)

    proc_status_df = pd.concat(proc_status_dfs, axis='index')

    # Save proc_status_df
    tracker_csv = f"{DATASET_ROOT}/derivatives/bagel.csv"
    proc_status_df = proc_status_df.drop(columns=COL_BIDS_ID_MANIFEST)
    proc_status_df.index.name = COL_BIDS_ID_MANIFEST
    proc_status_df.to_csv(tracker_csv)

    logger.info(f"Saved tracker-bagel to {tracker_csv}")

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to run trackers on various proc_pipes
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global config file for your nipoppy dataset', required=True)
    parser.add_argument('--dash_schema', type=str, help='path to dashboard schema to display tracker status', required=True)
    parser.add_argument('--pipelines', nargs='+', help='list of pipelines to track', required=True)
    parser.add_argument('--session_id', type=str, default="ALL", help='session_id (default = ALL')
    args = parser.parse_args()

    # read global configs
    global_config_file = args.global_config

    # Read global configs
    with open(global_config_file, 'r') as f:
        global_configs = json.load(f)
    
    # Driver code
    dash_schema_file = args.dash_schema
    pipelines = args.pipelines
    session_id = args.session_id

    run(global_configs, dash_schema_file, pipelines, session_id)
