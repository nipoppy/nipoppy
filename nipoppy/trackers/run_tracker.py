#!/usr/bin/env python
import argparse
import json
import bids 
import json
import warnings
from pathlib import Path
import pandas as pd

import nipoppy.workflow.logger as my_logger
from nipoppy.trackers.tracker import Tracker, get_start_time, get_end_time, UNAVAILABLE, TRUE
from nipoppy.trackers import fs_tracker, fmriprep_tracker, mriqc_tracker, tractoflow_tracker
from nipoppy.workflow.utils import (
    BIDS_SUBJECT_PREFIX,
    BIDS_SESSION_PREFIX,
    COL_SUBJECT_MANIFEST,
    COL_BIDS_ID_MANIFEST,
    COL_SESSION_MANIFEST,
    COL_CONV_STATUS, 
    DNAME_BACKUPS_BAGEL,
    FNAME_BAGEL,
    FNAME_DOUGHNUT,
    load_doughnut,
    save_backup,
    session_id_to_bids_session,
)

# Globals
PIPELINE_STATUS_COLUMNS = "PIPELINE_STATUS_COLUMNS"
pipeline_tracker_config_dict = {
    "heudiconv": bids_tracker.tracker_configs, 
    "freesurfer": fs_tracker.tracker_configs,
    "fmriprep": fmriprep_tracker.tracker_configs,
    "mriqc": mriqc_tracker.tracker_configs,
    "tractoflow": tractoflow_tracker.tracker_configs,
}
BIDS_PIPES = ["mriqc","fmriprep", "tractoflow"]

def run(global_configs, dash_schema_file, pipelines, session_id="ALL", run_id=1, logger=None, log_level="INFO"):
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
        log_file = f"{log_dir}/tracker.log"
        logger = my_logger.get_logger(log_file, level=log_level)

    logger.info(f"Tracking pipelines: {pipelines}")

    if session_id == "ALL":
        sessions = global_configs["SESSIONS"]
    else:
        sessions = [f"ses-{session_id}"]

    logger.info(f"tracking session_ids: {session_ids}")    

    for pipeline in pipelines:
        pipe_tracker = Tracker(global_configs, dash_schema_file, pipeline) 
        
        # TODO revise tracker class
        # DATASET_ROOT, session_ids, version = pipe_tracker.get_global_configs()
        if pipeline == "heudiconv":
            version = global_configs["BIDS"][pipeline]["VERSION"]
        else:
            version = global_configs["PROC_PIPELINES"][pipeline]["VERSION"]
            
        schema = pipe_tracker.get_dash_schema()
        tracker_configs = pipeline_tracker_config_dict[pipeline]

        # Grab BIDS participants from the doughnut
        doughnut_file = f"{DATASET_ROOT}/scratch/raw_dicom/{FNAME_DOUGHNUT}"
        doughnut_df = load_doughnut(doughnut_file)
        participants_total = doughnut_df[doughnut_df[COL_CONV_STATUS]][COL_BIDS_ID_MANIFEST].unique()
        n_participants_total = len(participants_total)

        logger.info("-"*50)
        logger.info(f"pipeline: {pipeline}, version: {version}")
        logger.info(f"n_participants_total: {n_participants_total}, session_ids: {session_ids}")
        logger.info("-"*50)

        status_check_dict = pipe_tracker.get_pipe_tasks(tracker_configs, PIPELINE_STATUS_COLUMNS, pipeline, version)

        # only use non-prefixed columns at this stage
        # for prefixed columns we need to generate the column name
        dash_col_list = list(key for key, value in schema["GLOBAL_COLUMNS"].items() if not value["IsPrefixedColumn"])

        for session_id in session_ids:
            session = session_id_to_bids_session(session_id)
            logger.info(f"Checking session: {session}")

            participants_session = doughnut_df[(doughnut_df[COL_BIDS_ID_MANIFEST].isin(participants_total)) & (doughnut_df[COL_SESSION_MANIFEST] == session)][COL_BIDS_ID_MANIFEST].drop_duplicates().astype(str).str.strip().values
            n_participants_session = len(participants_session)
            logger.info(f"n_participants_session: {n_participants_session}")

            _df = pd.DataFrame(index=participants_session, columns=dash_col_list)
            _df[COL_SESSION_MANIFEST] = session
            _df["pipeline_name"] = pipeline
            _df["pipeline_version"] = version
            _df["has_mri_data"] = TRUE # everyone in the doughnut file has MRI data

            # Set correct dtype based on dash schema to avoid panads warning
            # i.e. "FutureWarning: Setting an item of incompatible dtype"
            dash_col_dtype = "str"
            for dash_col, _ in status_check_dict.items():
                _df[dash_col] = _df[dash_col].astype(dash_col_dtype)
                
            # BIDS (i.e. heudiconv tracker is slightly different than proc_pipes)
            if pipeline == "heudiconv":
                # Generate BIDSLayout only once per tracker run and not for each participant
                bids_layout = bids.BIDSLayout(bids_dir, validate=False)
                logger.debug(f"bids_dir: {bids_dir}")
                logger.debug(f"bids_layout: {bids_layout.get_subjects()}")
                
            fpath_bagel = Path(dataset_root, 'derivatives', FNAME_BAGEL)
            if fpath_bagel.exists():
                df_bagel_old_full = load_bagel(fpath_bagel)

                df_bagel_old_session = df_bagel_old_full.loc[df_bagel_old_full[COL_SESSION_MANIFEST] == session]
                old_participants_session = set(df_bagel_old_session[COL_BIDS_ID_MANIFEST])
                old_pipelines_session = set(df_bagel_old_session['pipeline_name'])
                
                # make sure the number of participants is consistent across pipelines
                if set(participants_session) != old_participants_session and not old_pipelines_session.issubset(set(pipelines)):
                    warnings.warn(
                        f'The existing bagel file might be obsolete (participant list does not match the doughnut file for session {session})'
                        f'. Rerun the tracker script with --pipelines {" ".join(old_pipelines_session.union(pipelines))}'
                    )
                
                df_bagel_old = df_bagel_old_full.loc[
                    ~(
                        (df_bagel_old_full["pipeline_name"] == pipeline) &
                        (df_bagel_old_full["pipeline_version"] == version) &
                        (df_bagel_old_full[COL_SESSION_MANIFEST] == session)
                    )
                ]
                
            else:
                df_bagel_old = None
            
            for bids_id in participants_session:
                participant_id = doughnut_df[doughnut_df[COL_BIDS_ID_MANIFEST]==bids_id][COL_SUBJECT_MANIFEST].values[0]
                _df.loc[bids_id, COL_SUBJECT_MANIFEST] = participant_id
                _df.loc[bids_id, COL_BIDS_ID_MANIFEST] = bids_id

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
                        # TODO only check files listed in the tracker config
                        _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE # get_end_time(subject_dir)
                else:
                    logger.warning(f"Output for pipeline: {pipeline} not found for bids_id: {bids_id}, session: {session}")
                    for name in status_check_dict.keys():                    
                        _df.loc[bids_id,name] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_starttime"] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE

            _df = _df.reset_index(drop=True)

            # add old rows from other pipelines/sessions and sort for consistent order
            df_bagel: pd.DataFrame = pd.concat([df_bagel_old, _df], axis='index')
            df_bagel = df_bagel.sort_values(["pipeline_name", "pipeline_version", COL_BIDS_ID_MANIFEST], ignore_index=True)

            # don't write a new file if no changes
            try:
                if len(df_bagel.compare(df_bagel_old_full)) == 0:
                    logger.info(f'\nNo change in bagel file for pipeline {pipeline}, session {session}')
                    continue
            except Exception:
                pass
            
            # save bagel
            save_backup(df_bagel, fpath_bagel, DNAME_BACKUPS_BAGEL)

def load_bagel(fpath_bagel):
    def time_converter(value):
        # convert to datetime if possible
        if str(value) != UNAVAILABLE:
            return pd.to_datetime(value)
        return value
    
    df_bagel = pd.read_csv(
        fpath_bagel, 
        dtype={
            'has_mri_data': bool,
            'participant_id': str,
            'session': str,
        },
        converters={
            'pipeline_starttime': time_converter,
            'pipeline_endtime': time_converter,
        }
    )
   
    return df_bagel

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to run trackers on various proc_pipes
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global config file for your nipoppy dataset', required=True)
    parser.add_argument('--dash_schema', type=str, help='path to dashboard schema to display tracker status', required=True)
    parser.add_argument('--pipelines', nargs='+', help='list of pipelines to track', required=True)
    parser.add_argument('--session_id', type=str, default="ALL", help='session_id (default = ALL)')
    parser.add_argument('--log_level', type=str, default="INFO", help='log level')
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
    log_level = args.log_level

    run(global_configs, dash_schema_file, pipelines, session_id, log_level=log_level)
