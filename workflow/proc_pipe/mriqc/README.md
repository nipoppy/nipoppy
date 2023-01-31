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
- Use [eval_mriqc_results.py](https://github.com/InesGP/mr_proc/blob/main/workflow/proc_pipe/mriqc/eval_mriqc_results.py) to determine how many subjects successfully passed through the MRIQC pipeline
	- Mandatory: Pass in a [JSON configuration file](https://github.com/InesGP/mr_proc/blob/main/workflow/proc_pipe/mriqc/mriqc_config.json) that contains the input directory, the results directory, the absolute path to the list of subjects, the desired file types, the desired session ID and the output CSV filename
	- Multiple sessions can be evaluated, but each session will require a new job running this script
	- Optional: By default, the script will evaluate if T1w and BOLD MRI data participant files were processed, but other file types can be passed in through the JSON file
- Example command:
	- python eval.py mriqc_config.json >> RESULTS_DIR/mriqc_eval_err.log
- After a successful run of the script, a CSV file named by default ```**status.csv**``` should appear in the results directory along with an error output log meant to track errors that may occur
- An example status CSV snippet:
```
participant_id,session_id,T1w,BOLD
sub-01,01,Success,Success
sub-02,01,Success,Fail
sub-03,01,Success,Success
sub-04,01,Success,Success
sub-05,01,Fail,Success
sub-06,01,Success,Success
sub-07,01,Success,Success
sub-08,01,Fail,Fail
sub-09,01,Success,Success
```
