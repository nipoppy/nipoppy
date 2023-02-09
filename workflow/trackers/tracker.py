import json
import pandas as pd 

class tracker:
    # constructor
    def __init__(self, global_config_file, dash_schema_file, pipeline):
        self.pipeline = pipeline
        self.global_config_file = global_config_file
        self.dash_schema_file = dash_schema_file

    # class methods
    def get_global_configs(self):
        with open(self.global_config_file, 'r') as f:
            global_configs = json.load(f)

        self.mr_proc_root_dir = global_configs["DATASET_ROOT"]
        self.sessions = global_configs["SESSIONS"]
        self.version = global_configs["PROC_PIPELINES"][self.pipeline]["VERSION"] 

    def get_dash_fields(self):
        with open(self.dash_schema_file, 'r') as f:
            dash_schema = json.load(f)

        self.global_columns = list(dash_schema["GLOBAL_COLUMNS"].keys())
        self.pipeline_column_prefixes = list(dash_schema["PIPELINE_COLUMN_PREFIXES"].keys())

    def get_pipe_tasks(self, tracker_configs):
        task_dict = {}
        for prefix in self.pipeline_column_prefixes:
            for task, func in tracker_configs[prefix].items():
                col_name = f"{prefix}{task}"            
                task_dict[col_name] = func 
        return task_dict
