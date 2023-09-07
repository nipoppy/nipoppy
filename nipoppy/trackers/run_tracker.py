#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import pandas as pd

import nipoppy.workflow.logger as my_logger
from nipoppy.trackers.tracker import Tracker, get_start_time, get_end_time, UNAVAILABLE, TRUE
from nipoppy.trackers import fs_tracker, fmriprep_tracker, mriqc_tracker, tractoflow_tracker
from nipoppy.workflow.utils import (
    COL_SUBJECT_MANIFEST,
    COL_BIDS_ID_MANIFEST,
    COL_SESSION_MANIFEST,
    COL_CONV_STATUS, 
    DNAME_BACKUPS_BAGELS,
    FNAME_BAGEL,
    load_status,
    save_backup,
    session_id_to_bids_session,
)

# Globals
PIPELINE_STATUS_COLUMNS = "PIPELINE_STATUS_COLUMNS"
pipeline_tracker_config_dict = {
    "freesurfer": fs_tracker.tracker_configs,
    "fmriprep": fmriprep_tracker.tracker_configs,
    "mriqc": mriqc_tracker.tracker_configs,
    "tractoflow": tractoflow_tracker.tracker_configs,
}
BIDS_PIPES = ["mriqc","fmriprep", "tractoflow"]

def run(global_configs, dash_schema_file, pipelines, session_id="ALL", run_id=1, logger=None):
    """ driver code running pipeline specific trackers
    """
    DATASET_ROOT = global_configs["DATASET_ROOT"]

    # logging
    log_dir = f"{DATASET_ROOT}/scratch/logs/"
    if logger is None:
        log_file = f"{log_dir}/mriqc.log"
        logger = my_logger.get_logger(log_file)

    logger.info(f"Tracking pipelines: {pipelines}")

    if session_id == "ALL":
        session_ids = global_configs["SESSIONS"]
    else:
        session_ids = [session_id]

    logger.info(f"tracking session_ids: {session_ids}")    

    for pipeline in pipelines:
        pipe_tracker = Tracker(global_configs, dash_schema_file, pipeline) 
        
        mr_proc_root_dir, session_ids, version = pipe_tracker.get_global_configs()
        schema = pipe_tracker.get_dash_schema()
        tracker_configs = pipeline_tracker_config_dict[pipeline]

        # Grab BIDS participants from the doughnut
        doughnut_file = f"{DATASET_ROOT}/scratch/raw_dicom/doughnut.csv"
        doughnut_df = load_status(doughnut_file)
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
            _df["has_mri_data"] = TRUE # everyone in the status file has MRI data

            tracker_csv = Path(mr_proc_root_dir, 'derivatives', FNAME_BAGEL)
            if tracker_csv.exists():
                old_proc_status_df_full = load_bagel(tracker_csv)

                old_proc_status_df_session = old_proc_status_df_full.loc[old_proc_status_df_full[COL_SESSION_MANIFEST] == session]
                old_participants_session = set(old_proc_status_df_session[COL_BIDS_ID_MANIFEST])
                old_pipelines_session = set(old_proc_status_df_session['pipeline_name'])
                
                # make sure the number of participants is consistent across pipelines
                if set(participants_session) != old_participants_session and not old_pipelines_session.issubset(set(pipelines)):
                    raise RuntimeError(
                        f'The existing processing status file might be obsolete (participant list does not match the status file for session {session})'
                        f'. Rerun the tracker script with --pipelines {" ".join(old_pipelines_session.union(pipelines))}'
                    )
                
                old_proc_status_df = old_proc_status_df_full.loc[
                    ~(
                        (old_proc_status_df_full["pipeline_name"] == pipeline) &
                        (old_proc_status_df_full["pipeline_version"] == version) &
                        (old_proc_status_df_full[COL_SESSION_MANIFEST] == session)
                    )
                ]
                
            else:
                old_proc_status_df = None
            
            for bids_id in participants_session:
                participant_id = doughnut_df[doughnut_df[COL_BIDS_ID_MANIFEST]==bids_id][COL_SUBJECT_MANIFEST].values[0]
                _df.loc[bids_id, COL_SUBJECT_MANIFEST] = participant_id
                _df.loc[bids_id, COL_BIDS_ID_MANIFEST] = bids_id

                if pipeline == "freesurfer":
                    subject_dir = f"{DATASET_ROOT}/derivatives/{pipeline}/v{version}/output/ses-{session_id}/{bids_id}" 
                elif pipeline in BIDS_PIPES:
                    subject_dir = f"{DATASET_ROOT}/derivatives/{pipeline}/v{version}/output/{bids_id}" 
                else:
                    logger.info(f"unknown pipeline: {pipeline}")
                    
                dir_status = Path(subject_dir).is_dir()
                logger.debug(f"subject_dir:{subject_dir}, dir_status: {dir_status}")
                
                if dir_status:                
                    for name, func in status_check_dict.items():
                        status = func(subject_dir, session_id, run_id)
                        logger.info(f"task_name: {name}, status: {status}")
                        _df.loc[bids_id,name] = status
                        _df.loc[bids_id,"pipeline_starttime"] = get_start_time(subject_dir)
                        _df.loc[bids_id,"pipeline_endtime"] = get_end_time(subject_dir)
                else:
                    logger.error(f"Output for pipeline: {pipeline} not found for bids_id: {bids_id}, session: {session}")
                    for name in status_check_dict.keys():                    
                        _df.loc[bids_id,name] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_starttime"] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE

            _df = _df.reset_index(drop=True)

            # add old rows from other pipelines/sessions and sort for consistent order
            proc_status_df: pd.DataFrame = pd.concat([old_proc_status_df, _df], axis='index')
            proc_status_df = proc_status_df.sort_values(["pipeline_name", "pipeline_version", COL_BIDS_ID_MANIFEST], ignore_index=True)

            # don't write a new file if no changes
            try:
                if len(proc_status_df.compare(old_proc_status_df_full)) == 0:
                    logger.info(f'\nNo change for pipeline {pipeline}, session {session}')
                    continue
            except Exception:
                pass
            
            # save proc_status_df
            save_backup(proc_status_df, tracker_csv, DNAME_BACKUPS_BAGELS)

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
