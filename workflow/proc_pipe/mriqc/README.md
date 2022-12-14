# README

## Building MRIQC Pipeline
In order to run the MRIQC pipeline and exclude scans with the acquisition label, build a Docker image using the ```Dockerfile_mriqc_patch```. If a Singularity container is needed using the following command can transform a Docker image into a Singularity one:

```docker run -v /var/run/docker.sock:/var/run/docker.sock -v OUTPUT_PATH:/output --privileged -t --rm quay.io/singularity/docker2singularity:v2.6 DOCKER_IMAGE```

## Running MRIQC Scripts
In order run the MRIQC pipeline, use ```run_mriqc.py``` from the main branch under ```workflow/proc_pipe/scripts``` and either run directly or wrap in SGE/Slurm script to run on cluster. Pass in 
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
