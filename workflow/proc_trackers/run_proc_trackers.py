import os
import pandas as pd
import json
from proc_tracker import tracker
from fs_tracker_utils import tracker_configs

# Driver code
global_config_file = "/home/nikhil/projects/Parkinsons/ppmi/proc/global_configs.json"
dash_schema_file = "/home/nikhil/projects/neuroinformatics_tools/dash/schemas/proc_status_schema.json"
pipe = "freesurfer"

pipe_tracker = tracker(global_config_file, dash_schema_file, pipe)     
pipe_tracker.get_global_configs()
pipe_tracker.get_dash_fields()
version = pipe_tracker.version    
sessions = pipe_tracker.sessions 
n_sessions = len(sessions)

participants = ["sub-3801","sub-3833"]
n_participants = len(participants)

print(f"pipeline: {pipe}, version: {version}, sessions: {sessions}")
task_dict = pipe_tracker.get_pipe_tasks(tracker_configs)
n_tasks = len(task_dict)

proc_status_cols = pipe_tracker.global_columns + list(task_dict.keys())

print(f"tracking {n_participants} with {n_sessions} sessions, on {n_tasks} tasks")

proc_status_df = pd.DataFrame()
for session in sessions:
    _df = pd.DataFrame(index=participants, columns=proc_status_cols)
    _df = _df.drop(columns=["participant_id"]) # it's indexed already
    _df["session"] = session
    _df["pipeline"] = pipe
    _df["version"] = version
    
    for participant_id in participants:
        print(f"{participant_id}")

        subject_dir = f"{pipe_tracker.mr_proc_root_dir}/derivatives/{pipe}/v{version}/output/ses-{session}/{participant_id}" 

        for task_name, func in task_dict.items():
            status = func(subject_dir)
            print(f"task_name: {task_name}, status: {status}")
            _df.loc[participant_id,task_name] = status

    proc_status_df = proc_status_df.append(_df)

print(proc_status_df)
