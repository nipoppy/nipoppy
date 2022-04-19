# Simple guide for HeuDiConv BIDS dataset conversion scripts

This is the HeuDiConv scripts for both slurm and SGE HPC systems (e.g. Compute Canada/BIC server) for dicom to BIDS conversion with [HeuDiConv version 0.9.0](https://github.com/nipy/heudiconv/tree/v0.9.0).

## General information
Before conversion, we need additional 2 steps to prepare the raw data:

1) **Fix the studyID inconsistent error** with `studyID_fixer.py`, this happens usually because the subject was taken out of the scanner for some reasons during the scanning protocol. Unless you were sure that no other problems during the imaging process, you can simply force all the studyID of the dicom files the same as the first dicom file of this image (**WARNING: You can only do this when you are sure about all the details of the images acquisition. If not, please consult your imaging experts for further suggestions, and always backup your raw dataset!**);
2) **Reorganize the dicom folder** into **dataset/subject/session/imageID/\*.dcm** with **./reorganize_session.py --data PPMI** with the table downloaded together with the dataset (*../tab_data/PPMI_3T_sdMRI_3_07_2022.csv*).
    
There are 2 steps (runs) for HeuDiConv to convert the dicom dataset into nifti and organized in BIDS format, and they are: 

1) **heudiconv_run1** (*heudiconv_run1.sh*), HeuDiConv will go over all the dicom images and summarize the dicom info into a table for each subject in a hidden folder **PPMI_BIDS/.heudiconv/** within the BIDS output folder; 
2) **heudiconv_run2** (*heudiconv_run2.sh*), do the conversion, you need to give a heuristic file based on the dicom info to filter out the images you would like to convert (*Heuristics_PPMI_all.py*); 
  
There are basically 3 scripts for each run of HeuDiConv, including: 

   1. **Main script**, e.g. `heudiconv_run1.sh` (screening all the dicom info):
      1. Function: 1) Preparing the working directories (following compute canada conventions, like all the data in `~/scratch`): 2) Create subject list and save it as a file for latter use; 3)  Submit the computing task to compute canada with `sbatch`;
      2. Input: 1) the name of dataset you would like to convert, e.g. PPMI (assuming all BIDS formated PPMI dataset are in `~/scratch/PPMI`); 
      3. Output: 1) Standard [BIDS dataset](https://bids.neuroimaging.io/); 2) Running logs.
   2. **Computing node script**, e.g. `heudiconv_run1.slurm/sge` (the script will be submitted to the slurm cluster to run on each of the computing nodes);
      1. Function: The working horse of convertion on computing node of the cluster: 1) Preparing the working environment for singularity containers (you will need a valid freesurfer liscence for this, which will be mounted in the singularity container as well); 2) Running the preprocessing with singularity container; 3) Writing log file.
      2. Input: The name of dataset you would like to preprocess;
      3. Output:  1) Standard [fMRIPrep  outputs](https://fmriprep.org/en/stable/outputs.html) from each computing node; 2) Running log for each computing task.
   3. **Results collection script**, e.g. `heudiconv_run1.format` (Organize the converted results and logs, prepare for data transfer).  
      1. Function: Orgnizing and zipping the fMRIPrep ourputs and logs for data transfer:
      2. Input: The name of dataset you would like to preprocess;
      3. Output: ziped BIDS versoin dataset logs/heudiconv in `..res/`

## Use example (take PPMI as use case):
1. Give execution to the **main script**: e.g. ```chmod +x mr_proc/HeuDiConv/heudiconv_run1.sh```;
2. Run the **run1 main code**: e.g. ```./mr_proc/HeuDiConv/heudiconv_run1.sh PPMI sge Y``` (on BIC server);
3. After the run1 finished, run the **results collection code**, e.g. ```./mr_proc/HeuDiConv/heudiconv_run1.format PPMI sge```;
4. Run the **run2 main code**: e.g. ```./mr_proc/HeuDiConv/heudiconv_run2.sh PPMI sge all``` (on BIC server);
5. After the run2 finished, run the **results collection code**, e.g. ```./mr_proc/HeuDiConv/heudiconv_run2.format PPMI sge```;
```../res/PPMI_BIDS.zip```.

## Reminder
  If there is any problems that you have encountered when trying to resuse these scripts, just open an issue and I will try my best to help.
