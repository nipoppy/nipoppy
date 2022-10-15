# README

## Building MRIQC Pipeline
In order to run the MRIQC pipeline and exclude scans with the acquisition label, build a Docker image using the ```Dockerfile_mriqc_patch```. If a Singularity container is needed using the following command can transform a Docker image into a Singularity one:

```docker run -v /var/run/docker.sock:/var/run/docker.sock -v OUTPUT_PATH:/output --privileged -t --rm quay.io/singularity/docker2singularity:v2.6 DOCKER_IMAGE```

NOTE: Singularity v2.6 is used for compatibility with BIC but this may change in the future.

## Running MRIQC Scripts
In order run the MRIQC pipeline, use ```run_mriqc_sge.sh``` from the main branch under ```workflow/proc_pipe/scripts``` and pass in the absolute path to the data directory, the absolute path to the results directory and the path with the participants list as arguments as shown below:

```qsub run_mriqc_sge.sh -d DATA_DIR -r RESULTS_DIR -p PARTICIPANT_LIST -c CONTAINER_DIR```

In order to evaluate how many subjects successfully passed through the MRIQC pipeline, run ```eval_mriqc_results.py``` from the main branch under ```workflow/proc_pipe/scripts```. The script requires a JSON configuration file with the input directory, the path with the result file, the path to the list of subjects and the desired file names to evaluate as shown below:

```{
	"input_dir": INPUT_DIR,
    	"results_file": RESULTS_FILE,
    	"subject_list": PARTICIPANT_FILE
    	"file_names": ["acq_GREMT", "acq_ADNI", "acq_grappa2"]
}```

NOTE: When running the scripts, modifications might need to be made to the SGE components of the job, i.e. where to email notifications, where to put the output log, how many array jobs to run, etc.
