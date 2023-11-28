import datetime
import glob
import json 
import os
from pathlib import Path

# Status flags
SUCCESS="SUCCESS"
FAIL="FAIL"
INCOMPLETE="INCOMPLETE"
UNAVAILABLE="UNAVAILABLE"

# boolean values
TRUE=True
FALSE=False

class Tracker:
    # constructor
    def __init__(self, global_configs, dash_schema_file, pipeline):
        self.pipeline = pipeline
        self.global_configs = global_configs
        self.dash_schema_file = dash_schema_file

    # class methods
    def get_global_configs(self):
        global_configs = self.global_configs
        dataset_root = global_configs["DATASET_ROOT"]
        sessions = global_configs["SESSIONS"]
        version = global_configs["PROC_PIPELINES"][self.pipeline]["VERSION"] 
        return dataset_root, sessions, version

    def get_dash_schema(self):
        with open(self.dash_schema_file, 'r') as f:
            self.dash_schema = json.load(f)

        return self.dash_schema

    def get_pipe_tasks(self, tracker_configs, col_group, pipeline, version):
        task_dict = self.dash_schema[col_group]
        status_check_dict = {}
        for k,v in task_dict.items():     
            if k in tracker_configs.keys():
                if v["IsPrefixedColumn"]:
                    prefixed_task_dict = tracker_configs[k]
                    for pk, pv in prefixed_task_dict.items():
                        status_check_dict[f"{k}{pipeline}-{version}__{pk}"] = pv
                else:    
                    status_check_dict[k] = tracker_configs[k]
            
            else: 
                is_req = bool(v["IsRequired"])
                if is_req:
                    print(f"Mandatory task: {k} not found in tracker_config dictionary")
                
        return status_check_dict


def get_start_time(subject_dir):
    # file modification timestamp of a file
    m_time = os.path.getmtime(subject_dir)
    # convert timestamp into DateTime object
    dt_m = datetime.datetime.fromtimestamp(m_time)
    return dt_m

def get_end_time(subject_dir):

    # find all the files
    fpaths = glob.glob(str(Path(subject_dir, '**', '*')))

    # get the timestamps
    timestamps = [
        datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
        for fpath in fpaths
    ]

    # get the latest time
    return max(timestamps)
