# Handling of Tractoflow inputs

## The process

Currently there is a single script, `scripts/mk_tracto_job.sh`, that when provided with a subject ID will create and SGE job file. Variables such as `$BIDSDIR`, `$OUTPUT`, and `$LOGDIR` need to be redirected to a new dataset. There is a second script that is just a `find` call to the BIDS dir to get and pass the subject IDs to `mk_tracto_job.sh`. These could be modified to be set as input variables to more closely match the fmriprep approach, but that's a minor TODO for now.

Despite coming from a BIDS layout, I have to use the "legacy" (?) input structure of the files for tractoflow to process them. The BIDS reader works fine, but it can only handle 1 configuration of files, which we don't have. There is currently no way to modify the BIDS reader to function differently or make a different kind of selection. This is a limitation on BIDS Apps as a whole to a certain extent. The solution is to make a temporary job directory and symlink the desired files from BIDS into simplified structure.

This is something that will need to be checked for every dataset this process is run on. Depending on the input files, effectively every dataset will need to be passed differently OR produce outputs in a slightly different folder. There are many different (and usable) configuration of files for this stage and they need to be handled differently. The most imporant things to know:
- Is there a forward / reverse phase encoded sequence (AP/PA, LR/RL)?
- Are they both full sequences, or is one just b0s?
- Checking the bvec orientation. During conversion to .nii.gz was RAS or LAS used?
  - a flip may be necessary to correct this if the orientation of the file is modified.

With the input folder specified, the tractoflow pipeline can be called. The process runs every step of the pipeline and creates the nextflow output directory structure of the tractoflow processes. This step either succeeds or fails as a whole unit. While a tractoflow process can be resumed, it is challenging / impossible to modify an already called process. Importantly, if a single step fail (segmentation, tracking mask, etc.) there's not an easy way to redo subsequent steps to correct them. The whole process needs to be rerun with the modifications at the call. There may be a better way within nextflow, but then we are not using BIDS as a storage standard. Because we are not keeping the intermediary folder structure, the final files are moved to a BIDS-derivative structure.

Most of the diffusion BIDS derivatives do not have a finalized set of metadata features to be created. I followed the BEP proposal [here](https://github.com/bids-standard/bids-bep016/blob/bep-016/src/05-derivatives/05-diffusion-derivatives.md) and captured as many of the fields as possible. This process is fragile and may have errors because they're just echo statements to track some basic provenance and fitting parameters. This is not robust to different inputs, but until the BEP is merged into the standard, it's all tentative anyway. 

## Dependencies

### Singularity

As long as singularity v3 is on the path, things should be fine. In theory, tractoflow can handle diffent container environments.

### Nextflow

Tractoflow uses the [nextflow](https://www.nextflow.io) scripting engine to run the modules it contains. Frankly, I don't know what this additional markup helps us solve because it makes it harder to run the commands, find the calls that are used for any given process, and makes going into and out of BIDS an added challenge.

The dependency is easy enough to install. I simply add the utility to the path at the top of the script, similar to how singularity is activated.

### jq

I use jq to write out the .json sidecars for the resulting BIDS files. Technically, all it is doing is adding the spacing / line breaks to the echo statements. This isn't strictly necessary, but it keeps the style of the written outputs inline with fmriprep sidecar formatting.
