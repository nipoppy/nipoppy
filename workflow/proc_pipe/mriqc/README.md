# README

## 1. Running MRIQC Scripts

### 1.1 Run MRIQC
- Use [run_mriqc.py](https://github.com/InesGP/mr_proc/blob/main/workflow/proc_pipe/mriqc/run_mriqc.py) to run MRIQC pipeline directly or wrap the script in an SGE/Slurm script to run on cluster
	- Mandatory: Pass in the absolute path to the data directory to **`global_config`**
	- Mandatory: Pass in the absolute path to the results directory to **`result_dir`**
	- Mandatory: Pass in the absolute path to the participants list to **`participant_list`**
	- Mandatory: Pass in the absolute path to where the container is located to **`container`**`
	- Mandatory: Pass in the index of which subject to run from the participants list to **`index`**
- Example command:
	- python run_mriqc.py --global_config DATA_DIR --result_dir RESULTS_DIR --participant_list PARTICIPANT_LIST --container CONTAINER_DIR --index INDEX
- MRIQC processes the participants and produces image quality metrics from structural (T1w and T2w) and functional MRI data (see [MRIQC](https://mriqc.readthedocs.io/en/latest/) for details)
- The script generates the output and the job log in the listed **`result_dir`**
- A run for a participant is considered successful when the participant's log file reads **`Participant level finished successfully`**
- The Dockerfile in this directory can be used to build the MRIQC pipeline which processes the data

### 1.2 Evaluate MRIQC Results
- Use [mriqc_tracker.py](https://github.com/InesGP/mr_proc/blob/main/workflow/proc_pipe/mriqc/eval_mriqc_results.py) to determine how many subjects successfully passed through the MRIQC pipeline
	- Mandatory: Pass in a [JSON configuration file](https://github.com/InesGP/mr_proc/blob/main/workflow/proc_pipe/mriqc/mriqc_config.json) that contains the input directory, the results directory, the subject ID and the desired session ID
	- Multiple sessions can be evaluated, but each session will require a new job running this script
- Example command:
	- python mriqc_tracker.py mriqc_config.json
- After a successful run of the script, a dictionary called `tracker_configs` is returned contained whether the subject passed through the pipeline successfully
