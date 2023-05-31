#!/usr/bin/env python

import argparse
from pathlib import Path

import pandas as pd

from trackers.tracker import tracker, get_start_time
from trackers import fs_tracker, fmriprep_tracker, mriqc_tracker
# from workflow.utils import load_manifest, save_backup # TODO once other PR is merged

# Status flags
SUCCESS="SUCCESS"
FAIL="FAIL"
INCOMPLETE="INCOMPLETE"
UNAVAILABLE="UNAVAILABLE"

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

    proc_status_dfs = [] # list of dataframes
    for pipeline in pipelines:
        pipe_tracker = tracker(global_config_file, dash_schema_file, pipeline) 
        
        mr_proc_root_dir, session_ids, version = pipe_tracker.get_global_configs()
        schema = pipe_tracker.get_dash_schema()
        tracker_configs = pipeline_tracker_config_dict[pipeline]

        mr_proc_manifest = f"{mr_proc_root_dir}/tabular/mr_proc_manifest.csv"
        manifest_df = pd.read_csv(mr_proc_manifest, converters={'datatype': pd.eval}) # TODO change to workflow.utils.load_manifest()
        participants = manifest_df[~manifest_df["bids_id"].isna()]["bids_id"].drop_duplicates().astype(str).str.strip().values
        n_participants = len(participants)

        print("-"*50)
        print(f"pipeline: {pipeline}, version: {version}")
        print(f"n_participants: {n_participants}, session_ids: {session_ids}")
        print("-"*50)

        status_check_dict = pipe_tracker.get_pipe_tasks(tracker_configs, PIPELINE_STATUS_COLUMNS, pipeline, version)

        # only use non-prefixed columns at this stage
        # for prefixed columns we need to generate the column name
        dash_col_list = list(key for key, value in schema["GLOBAL_COLUMNS"].items() if not value["IsPrefixedColumn"])

        for session_id in session_ids:
            print(f"Checking session: {session_id}")    
            _df = pd.DataFrame(index=participants, columns=dash_col_list)          
            _df["session"] = session_id
            _df["pipeline_name"] = pipeline
            _df["pipeline_version"] = version
            _df["has_mri_data"] = "true" # everyone with a session value has MRI data
            
            n_participants = 0
            for bids_id in participants:
                participant_id = manifest_df[manifest_df["bids_id"]==bids_id]["participant_id"].values[0]
                _df.loc[bids_id,"participant_id"] = participant_id
                # print(f"bids_id: {bids_id}, participant_id: {participant_id}")

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
                        _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE # TODO
                    n_participants += 1
                else:
                    # print(f"Pipeline output not found for bids_id: {bids_id}, session: {session}")
                    for name in status_check_dict.keys():                    
                        _df.loc[bids_id,name] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_starttime"] = UNAVAILABLE
                        _df.loc[bids_id,"pipeline_endtime"] = UNAVAILABLE

                if testing and n_participants > N_TESTING:
                    break

            proc_status_dfs.append(_df)

    proc_status_df = pd.concat(proc_status_dfs, axis='index')

    # Save proc_status_df
    tracker_csv = f"{mr_proc_root_dir}/derivatives/bagel.csv"
    proc_status_df = proc_status_df.drop(columns="bids_id")
    proc_status_df.index.name = "bids_id"
    proc_status_df.to_csv(tracker_csv)

    print(f"Saved to {tracker_csv}")

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
