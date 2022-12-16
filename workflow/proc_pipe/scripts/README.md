# README

## Running MRIQC Scripts
In order run the MRIQC pipeline, use ```run_mriqc_sge.py``` and either run directly or wrap in SGE/Slurm script to run on cluster. Pass in 
* the absolute path to the data directory
* the absolute path to the results directory
* the absolute path to the participants list 
* the absolute path to where the container is located
* the index of which subject to run from the participants list

```
python run_mriqc.py --global_config DATA_DIR --result_dir RESULTS_DIR --participant_list PARTICIPANT_LIST --container CONTAINER_DIR --index INDEX
```

In order to evaluate how many subjects successfully passed through the MRIQC pipeline, run ```eval_mriqc_results.py```. The script requires a JSON configuration file with the input directory, the path with the result file, the path to the list of subjects and the desired file names to evaluate as shown below:

```{
	"input_dir": INPUT_DIR,
    	"results_file": RESULTS_FILE,
    	"subject_list": PARTICIPANT_FILE
    	"file_names": ["acq_GREMT", "acq_ADNI", "acq_grappa2"]
}```

