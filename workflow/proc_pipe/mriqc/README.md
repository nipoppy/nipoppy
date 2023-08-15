# README

## 1. Running MRIQC Scripts

### 1.1 Run MRIQC
- Use [run_mriqc.py](https://github.com/neurodatascience/nipoppy/blob/main/workflow/proc_pipe/mriqc/run_mriqc.py) to run MRIQC pipeline directly or wrap the script in an SGE/Slurm script to run on cluster
	- Mandatory: Pass in the absolute path to the data directory to **`global_config`**

- Example command:
	``` python run_mriqc.py --global_config CONFIG.JSON --participant_id 001 --output_dir OUTPUT_DIR_PATH --session_id 01 ```
	- The format for the JSON configuration file to be passed to the script is shown [here](https://github.com/neurodatascience/nipoppy/blob/main/sample_global_configs.json)
	
- MRIQC processes the participants and produces image quality metrics from structural (T1w and T2w) and functional MRI data (see [MRIQC](https://mriqc.readthedocs.io/en/latest/) for details)
- The script generates the output and the job log in the listed **`output_dir`**
- A run for a participant is considered successful when the participant's log file reads **`Participant level finished successfully`**
- The Dockerfile in this directory can be used to build the MRIQC pipeline which processes the data

### 1.2 Evaluate MRIQC Results
- Use [mriqc_tracker.py](https://github.com/neurodatascience/nipoppy/blob/main/trackers/mriqc_tracker.py) to determine how many subjects successfully passed through the MRIQC pipeline
	- Mandatory: Pass in the subject directory as an argument
	- Multiple sessions can be evaluated, but each session will require a new job running this script
- Example command:
```pycon
>>> results = {"pipeline_complete': mriqc_tracker.eval_mriqc(subject_dir, session_id)}
>>> results
 SUCCESS
>>> results = {"MRIQC_BOLD': mriqc_tracker.check_bold(subject_dir, session_id)}
>>> results
 FAIL
```
- After a successful run of the script, a dictionary called `tracker_configs` is returned contained whether the subject passed through the pipeline successfully
