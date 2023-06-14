#!/usr/bin/env python

import argparse
from pathlib import Path

import pandas as pd

from trackers.tracker import Tracker, get_start_time, get_end_time, UNAVAILABLE, TRUE
from trackers import fs_tracker, fmriprep_tracker, mriqc_tracker
from workflow.utils import load_manifest, save_backup

DNAME_BACKUPS_BAGEL = '.bagel'

# Globals
PIPELINE_STATUS_COLUMNS = "PIPELINE_STATUS_COLUMNS"
pipeline_tracker_config_dict = {
    "freesurfer": fs_tracker.tracker_configs,
    "fmriprep": fmriprep_tracker.tracker_configs,
    "mriqc": mriqc_tracker.tracker_configs
}
BIDS_PIPES = ["mriqc","fmriprep"]

# number of participants to check per session when testing
N_TESTING = 10

def run(global_config_file, dash_schema_file, pipelines, run_id=1, testing=False):
    """ driver code running pipeline specific trackers
    """

    for pipeline in pipelines:
        pipe_tracker = Tracker(global_config_file, dash_schema_file, pipeline) 
        
        mr_proc_root_dir, session_ids, version = pipe_tracker.get_global_configs()
        schema = pipe_tracker.get_dash_schema()
        tracker_configs = pipeline_tracker_config_dict[pipeline]

        mr_proc_manifest = f"{mr_proc_root_dir}/tabular/mr_proc_manifest.csv"
        manifest_df = load_manifest(mr_proc_manifest)
        participants = manifest_df[~manifest_df["bids_id"].isna()]["bids_id"].drop_duplicates().astype(str).str.strip().values
        n_participants = len(participants)

        tracker_csv = Path(mr_proc_root_dir, 'derivatives', 'bagel.csv')
        if tracker_csv.exists():
            old_proc_status_df_full = load_bagel(tracker_csv)
            
            # make sure the number of participants is consistent across pipelines
            if set(participants) != set(old_proc_status_df_full['bids_id'].to_list()) and set(pipelines) != set(old_proc_status_df_full['pipeline_name'].to_list()):
                raise RuntimeError(
                    'The existing processing status file is obsolete (participant list does not match the manifest)'
                    f'. Rerun the tracker script with --pipelines {" ".join(set(old_proc_status_df_full["pipeline_name"]).union(pipelines))}'
                )
            
            old_proc_status_df = old_proc_status_df_full.loc[~((old_proc_status_df_full["pipeline_name"] == pipeline) & (old_proc_status_df_full["pipeline_version"] == version))]
            
        else:
            old_proc_status_df = None

        print("-"*50)
        print(f"pipeline: {pipeline}, version: {version}")
        print(f"n_participants: {n_participants}, session_ids: {session_ids}")
        print("-"*50)

        status_check_dict = pipe_tracker.get_pipe_tasks(tracker_configs, PIPELINE_STATUS_COLUMNS, pipeline, version)

        # only use non-prefixed columns at this stage
        # for prefixed columns we need to generate the column name
        dash_col_list = list(key for key, value in schema["GLOBAL_COLUMNS"].items() if value["IsRequired"] and not value["IsPrefixedColumn"])

        proc_status_session_dfs = [] # list of dataframes
        for session_id in session_ids:
            print(f"Checking session: {session_id}")    
            _df = pd.DataFrame(index=participants, columns=dash_col_list)          
            _df["session"] = session_id
            _df["pipeline_name"] = pipeline
            _df["pipeline_version"] = version
            _df["bids_id"] = _df.index
            _df["participant_id"] = manifest_df.drop_duplicates("bids_id").set_index("bids_id").loc[participants, "participant_id"]
            _df["has_mri_data"] = TRUE # everyone with a session value has MRI data
            
            n_participants = 0
            for bids_id in participants:
                if pipeline == "freesurfer":
                    subject_dir = f"{mr_proc_root_dir}/derivatives/{pipeline}/v{version}/output/ses-{session_id}/{bids_id}" 
                elif pipeline in BIDS_PIPES:
                    subject_dir = f"{mr_proc_root_dir}/derivatives/{pipeline}/v{version}/output/{bids_id}" 
                else:
                    print(f"unknown pipeline: {pipeline}")
                    
                dir_status = Path(subject_dir).is_dir()
                # print(f"subject_dir:{subject_dir}, dir_status: {dir_status}")
                
                if dir_status:                
                    for name, func in status_check_dict.items():
                        status = func(subject_dir, session_id, run_id)
                        # print(f"task_name: {name}, status: {status}")
                        _df.loc[bids_id,name] = status
                    _df.loc[bids_id,"pipeline_starttime"] = get_start_time(subject_dir)
                    _df.loc[bids_id,"pipeline_endtime"] = get_end_time(subject_dir)
                    n_participants += 1
                else:
                    # print(f"Pipeline output not found for bids_id: {bids_id}, session: {session}")
                    for name in status_check_dict.keys():                    
                        _df.loc[bids_id,name] = UNAVAILABLE
                    _df.loc[bids_id,"pipeline_starttime"] = UNAVAILABLE
                    _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE

                # don't check all participants if testing
                if testing and n_participants > N_TESTING:
                    break

            proc_status_session_dfs.append(_df)

        # new rows for this pipeline
        pipeline_proc_status_df = pd.concat(proc_status_session_dfs, axis='index').reset_index(drop=True)

        # add old rows from other pipelines and sort for consistent order
        proc_status_df: pd.DataFrame = pd.concat([old_proc_status_df, pipeline_proc_status_df], axis='index')
        proc_status_df = proc_status_df.sort_values(["pipeline_name", "pipeline_version", "bids_id"], ignore_index=True)

        # don't write a new file if no changes
        try:
            if len(proc_status_df.compare(old_proc_status_df_full)) == 0:
                print(f'\nNo change for pipeline {pipeline}')
                continue
        except Exception:
            pass
        
        # save proc_status_df
        save_backup(proc_status_df, tracker_csv, DNAME_BACKUPS_BAGEL)

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
    parser.add_argument('--global_config', type=str, help='path to global config file for your mr_proc dataset', required=True)
    parser.add_argument('--dash_schema', type=str, help='path to dashboard schema to display tracker status', required=True)
    parser.add_argument('--pipelines', nargs='+', help='list of pipelines to track', required=True)
    parser.add_argument('--testing', action='store_true', help=f'only check first {N_TESTING} participants with MRI data')
    args = parser.parse_args()

    # read global configs
    global_config_file = args.global_config
    
    # Driver code
    dash_schema_file = args.dash_schema
    pipelines = args.pipelines

    print(f"Tracking pipelines: {pipelines}")

    testing = args.testing

    run(global_config_file, dash_schema_file, pipelines, testing=testing)
