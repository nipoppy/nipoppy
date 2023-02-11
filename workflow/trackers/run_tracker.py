import os
import pandas as pd
import json
from pathlib import Path
import argparse
import datetime
from tracker import tracker, get_start_time
from fs_tracker_utils import tracker_configs

# Status flags
SUCCESS="SUCCESS"
FAIL="FAIL"
INCOMPLETE="INCOMPLETE"
UNAVAILABLE="UNAVAILABLE"

def run(global_config_file, dash_schema_file, pipelines):
    # Currently only tracking freesurfer
    pipeline = pipelines[0]

    pipe_tracker = tracker(global_config_file, dash_schema_file, pipeline) 
        
    mr_proc_root_dir, sessions, version = pipe_tracker.get_global_configs()
    schema = pipe_tracker.get_dash_schema()
    
    n_sessions = len(sessions)

    mr_proc_manifest = f"{mr_proc_root_dir}/tabular/demographics/mr_proc_manifest.csv"
    manifest_df = pd.read_csv(mr_proc_manifest)
    participants = manifest_df["participant_id"].astype(str).str.strip().values
    n_participants = len(participants)

    print("-"*50)
    print(f"pipeline: {pipeline}, version: {version}")
    print(f"n_participants: {n_participants}, sessions: {n_sessions}")
    print("-"*50)

    col_group = "PIPELINE_STATUS_COLUMNS"
    status_check_dict = pipe_tracker.get_pipe_tasks(tracker_configs, col_group)
    n_checks = len(status_check_dict)

    dash_col_list = list(schema["GLOBAL_COLUMNS"].keys()) 

    proc_status_df = pd.DataFrame()
    for session in sessions:
        print(f"Checking session: {session}")
        _df = pd.DataFrame(index=participants, columns=dash_col_list)
        _df = _df.drop(columns=["participant_id"]) # it's indexed already
        _df["session"] = session
        _df["pipeline_name"] = pipeline        
        _df["pipeline_version"] = version
        
        for participant_id in participants:
            print(f"participant_id: {participant_id}")

            subject_dir = f"{mr_proc_root_dir}/derivatives/{pipeline}/v{version}/output/ses-{session}/sub-{participant_id}" 

            dir_status = Path(subject_dir).is_dir()
            if dir_status:                
                for name, func in status_check_dict.items():
                    status = func(subject_dir)
                    print(f"task_name: {name}, status: {status}")
                    _df.loc[participant_id,name] = status
                    _df.loc[participant_id,"pipeline_starttime"] = get_start_time(subject_dir)
            else:
                print(f"Pipeline output not found for participant_id: {participant_id}, session: {session}")
                for name in status_check_dict.keys():                    
                    _df.loc[participant_id,name] = UNAVAILABLE
                    _df.loc[participant_id,"pipeline_starttime"] = UNAVAILABLE

        proc_status_df = proc_status_df.append(_df)

    # Save proc_status_df
    tracker_csv = f"{mr_proc_root_dir}/derivatives/bagel.csv"
<<<<<<< HEAD
    proc_status_df.index.name = "participant_id"
=======
>>>>>>> 02f04d949a7001e1b0f502df4d0eb6b602aa9713
    proc_status_df.to_csv(tracker_csv)

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to run trackers on various proc_pipes
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global config file for your mr_proc dataset')
    parser.add_argument('--dash_schema', type=str, help='path to dashboard schema to display tracker status')
    parser.add_argument('--pipelines', nargs='+', help='list of pipelines to track', required=True)
    args = parser.parse_args()

    # read global configs
    global_config_file = args.global_config
    
    # Driver code
    dash_schema_file = args.dash_schema
    pipelines = args.pipelines

<<<<<<< HEAD
    run(global_config_file, dash_schema_file, pipelines)
=======
    run(global_config_file, dash_schema_file, workflows)
>>>>>>> 02f04d949a7001e1b0f502df4d0eb6b602aa9713
