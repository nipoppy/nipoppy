import os
import pandas as pd
import json
from pathlib import Path
import argparse

from tracker import tracker
from fs_tracker_utils import tracker_configs


def run(global_config_file, dash_schema_file, workflows):
    # Currently only tracking freesurfer
    workflow = workflows[0]

    pipe_tracker = tracker(global_config_file, dash_schema_file, workflow)     
    pipe_tracker.get_global_configs()
    pipe_tracker.get_dash_fields()
    version = pipe_tracker.version    
    sessions = pipe_tracker.sessions 
    n_sessions = len(sessions)

    mr_proc_root_dir = pipe_tracker.mr_proc_root_dir
    
    mr_proc_manifest = f"{mr_proc_root_dir}/tabular/demographics/mr_proc_manifest.csv"
    manifest_df = pd.read_csv(mr_proc_manifest)
    participants = manifest_df["participant_id"].astype(str).str.strip().values
    n_participants = len(participants)

    print(f"workflow: {workflow}, version: {version}, sessions: {sessions}")
    task_dict = pipe_tracker.get_pipe_tasks(tracker_configs)
    n_tasks = len(task_dict)

    proc_status_cols = pipe_tracker.global_columns + list(task_dict.keys())

    print(f"tracking {n_participants} participants with {n_sessions} sessions, on {n_tasks} tasks")

    proc_status_df = pd.DataFrame()
    for session in sessions:
        _df = pd.DataFrame(index=participants, columns=proc_status_cols)
        _df = _df.drop(columns=["participant_id"]) # it's indexed already
        _df["session"] = session
        _df["workflow"] = workflow
        _df["version"] = version
        
        for participant_id in participants:
            print(f"{participant_id}")

            subject_dir = f"{pipe_tracker.mr_proc_root_dir}/derivatives/{workflow}/v{version}/output/ses-{session}/sub-{participant_id}" 

            for task_name, func in task_dict.items():
                status = func(subject_dir)
                # print(f"task_name: {task_name}, status: {status}")
                _df.loc[participant_id,task_name] = status

        proc_status_df = proc_status_df.append(_df)

    # Save proc_status_df
    tracker_csv = f"{mr_proc_root_dir}/derivatives/bagel.csv"
    proc_status_df.to_csv(tracker_csv, index=None)

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to run trackers on various proc_pipes
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--global_config', type=str, help='path to global config file for your mr_proc dataset')
    parser.add_argument('--dash_schema', type=str, help='path to dashboard schema to display tracker status')
    parser.add_argument('--workflows', nargs='+', help='list of workflows to track', required=True)
    args = parser.parse_args()

    # read global configs
    global_config_file = args.global_config
    
    # Driver code
    dash_schema_file = args.dash_schema
    workflows = args.workflows

    run(global_config_file, dash_schema_file, workflows)