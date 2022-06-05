# Simple guide for fmriprep scripts
This is the fMRIPrep scripts with slurm based HPC system (e.g. Compute Canada) for this ET structrual MRI analysis, it is adapted from the sample code provided by the [fMRIPrep official documents (version 1.5.1)](https://fmriprep.org/en/1.5.1/singularity.html), you can find more information regarding fMRIPrep in the official documents.
## General information
Based on different purposes of preprocessing, I provided 3 different versions of the fMRIPrep scripts: 1) **Anatomical preprocessing for a whole dataset (multiple subjects))** (fmriprep_anat.\*); 2) **Anatomical preprocessing for single subject** (fmriprep_anat_sub.\*, this is used in case you want to rerun the preprocessing for some specific single subject, I directly put the subject list I would like to rerun in this script); 3) **Anatomical and functional preprocessing for a whole dataset (multiple subjects)** (fmriprep_func.\*).
There are 3 scripts for each of these fMRIPrep preprocessing version, including: 
   1. **Main script**, e.g. `fmriprep_anat.sh` (preprocessing for only anatomical images):
      1. Function: 1) Preparing the working directories (following compute canada conventions, like all the data in `~/scratch`): 2) Create subject list and save it as a file for latter use; 3) Download the templates (with TemplateFlow) for fMRIPrep; 4) Submit the computing task to compute canada with `sbatch`;
      2. Input: 1) the name of dataset you would like to preprocess, e.g. PPMI (assuming all BIDS formated PPMI dataset are in `~/scratch/PPMI_BIDS`); 
      3. Output: 1) Standard [fMRIPrep  outputs](https://fmriprep.org/en/stable/outputs.html); 2) Running logs.
   2. **Computing node script**, e.g. `fmriprep_anat.slurm` (the script will be submitted to the slurm cluster to run on each of the computing nodes);
      1. Function: The working horse of calling fMRIPrep singularity containner to run the preprocessing on computing node of the cluster: 1) Preparing the working environment for singularity containers (you will need a valid freesurfer liscence for this, which will be mounted in the singularity container as well); 2) Running the preprocessing with singularity container; 3) Writing log file.
      2. Input: The name of dataset you would like to preprocess;
      3. Output:  1) Standard [fMRIPrep  outputs](https://fmriprep.org/en/stable/outputs.html) from each computing node; 2) Running log for each computing task.
   3. **Results collection script**, e.g. `fmriprep_anat.format` (Organize the preprocessed results and logs, prepare for data transfer).  
      1. Function: Orgnizing and zipping the fMRIPrep ourputs and logs for data transfer:
      2. Input: The name of dataset you would like to preprocess;
      3. Output: ziped fMRIPrep results/freesurfer results/logs in `/scratch/res/`
   4. **Special case: BIDS filter file**, e.g. `pre_opt.json` (json data file). We found some post-surgical sessions in the dataset and use this file to inform fMRIPrep not to process them.

## Use example (take PPMI as use case):
1. Give execution to the **main script**: e.g. `chmod +x ET_biomarker/scripts/fmriprep/fmriprep_anat.sh`;
2. Run the **main code**: e.g. `./ET_biomarker/scripts/fmriprep/fmriprep_anat.sh PPMI`;
3. After the preprocessing finished, run the **results collection code**, e.g. `./ET_biomarker/scripts/fmriprep/fmriprep_anat.format PPMI`.
4. Data ready for further analysis!!! You can find  `~/scratch/res/PPMI_fmriprep_anat_${FMRIPREP_VER}.tar.gz` (the fMRIPrep results), `~/scratch/res/PPMI_fmriprep_anat_freesurfer_${FMRIPREP_VER}.tar.gz` (the freesurfer results) and `PPMI_fmriprep_anat_log.tar.gz` (log file).

## Reminder
  0. If there is any problems that you have encountered when trying to resuse these scripts, just open an issue and I will try my best to help.
  1. If there are any running errors (indicated from slurm logs, ***.err), try to rerun the preprocessing for the single subject with more computing resources (cores/RAM/computing time), it works for most of time, if not, you need to check the data quality;
  2. Usually, the computing node does not have access to the Internet for security reasons, and make sure you have downloaded the templates with TemplateFlow before submitting the computing tasks.