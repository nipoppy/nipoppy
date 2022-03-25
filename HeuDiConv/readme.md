# Simple guide for HeuDiConv scripts
This is the HeuDiConv scripts with slurm based HPC system (e.g. Compute Canada) for this ET structrual MRI data conversion (from dicoms to BIDS nifti), it is adapted from the sample code provided by the [HeuDiConv official documents (version 0.5.4)](https://heudiconv.readthedocs.io/en/latest/), you can find more information regarding HeuDiConv in the official documents.
## General information
There are 2 steps (runs) for HeuDiConv to convert the dicom dataset into nifti and organized in BIDS format, we have scripts for both 2 runs, and they are: 

    1) **heudiconv_run1** (heudiconv_run1.\*), HeuDiConv will go over all the dicom images and summarize the dicom info into a table for each subject in a hidden folder `PPMI_BIDS/.heudiconv/*` within the BIDS output folder; 
    2) **heudiconv_run2** (heudiconv_run2.\*, this is the where the conversion is happening, you need to give a heuristic file based on the dicom info to filter out the images you would like to convert); 
    3) **Some other useful scripts**: 
        1) Hueristics for different datasets: e.g. `Heuristics_PPMI_T1.py` is the heuristic file for T1 images for PPMI dataset; 
        2) Jupyter notebook for analyzing the dicom info and creating heuristics, e.g. `session_sel.ipynb`;.
        3) Error handling scripts, e.g. `studyID_fixer.py` is for handling the studyID error during conversion, this happens usually because the subject was taken out of the scanner for some reasons during the scanning protocol, as long as you know there were no other problems, you can simply make all the studyID of the dicom images the same as the first dicom image of this subject (WARNING: You can only do this when you are sure about all the details of the images acquisitin. If not, please consult your imaging experts for further suggestions, and always backup your raw dataset!): 
        
There are basically 3 scripts for each run of HeuDiConv, including: 

   
   1. **Main script**, e.g. `heudiconv_run1.sh` (screening all the dicom info):
      1. Function: 1) Preparing the working directories (following compute canada conventions, like all the data in `~/scratch`): 2) Create subject list and save it as a file for latter use; 3)  Submit the computing task to compute canada with `sbatch`;
      2. Input: 1) the name of dataset you would like to convert, e.g. PPMI (assuming all BIDS formated PPMI dataset are in `~/scratch/PPMI`); 
      3. Output: 1) Standard [BIDS dataset](https://bids.neuroimaging.io/); 2) Running logs.
   2. **Computing node script**, e.g. `heudiconv_run1.slurm` (the script will be submitted to the slurm cluster to run on each of the computing nodes);
      1. Function: The working horse of convertion on computing node of the cluster: 1) Preparing the working environment for singularity containers (you will need a valid freesurfer liscence for this, which will be mounted in the singularity container as well); 2) Running the preprocessing with singularity container; 3) Writing log file.
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
