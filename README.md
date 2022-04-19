# mr_proc (workflow for standarized processing of MR images)
Process long and prosper

## Objective
This repo will contain container recipes and run scripts to 
    1. Standadized data i.e. convert DICOMs into BIDS
    2. Run commonly used image processing pipelines e.g. FreeSurfer, fMRIPrep

## Workflow steps

1. Gather dataset metadata (Required)
   - Create demograph.csv comprising participant IDs, visit, age, sex, and group (e.g. Dx) information. 
       - Note that demograph.csv corresponds to a single visit. If you have longitudinal data you will have to run this workflow multiple times. 
   - Create proc_tracker.csv comprising participant IDs from demograph.csv 
       - This will track the progress of processing workflow and any issues we encounter. 
2. Gather MRI acquisition protocols (Optional)
   - This lists all the modalities and acquisition protocols used duing scanning e.g. MPRAGE, 3DT1, FLAIR, RS-FMRI etc. 
3. DICOM organization (Required) 
   - DICOMs are available in various formats and disks. In this step we extract, copy, and rename DICOMs in a single directory for all participants listed in the metadata.csv. 
   - Participant ID convention is decided in this step during renaming. 
4. BIDS conversion using [Heudiconv](https://heudiconv.readthedocs.io/en/latest/) ([tutorial](https://neuroimaging-core-docs.readthedocs.io/en/latest/pages/heudiconv.html))
   - Specify Heudiconv container (i.e. Singularity image / recipe) 
   - Run single participant tests: 
       - Modify and run "./heudiconv_run1.sh" script with apporpriate local paths. This will generate list of available protocols from DICOM header. 
       - Manual update of heurisitic file using the enlisted protocols from run1. 
       - Modify and run "./heudiconv_run2.sh" script with apporpriate local paths. This will convert the DICOMs into NIFTIs along with sidecar JSONs and organize them based on your heuristic file.
       - Run BIDS validator. There are several options listed [here](https://github.com/bids-standard/bids-validator). Make sure you match the version of Heudiconv and BIDS validator standard. 
   - Run entire dataset (provided single participant test is successful) 
       - The script above work for single participant (i.e. single DICOM dir). The entire dataset can be BIDSified using a "for loop" or if you have access to a cluster you can run it parallel using heudiconv_run<>_sge.sh or heudiconv_run<>_slurm.sh queue submission scripts. 
       - Heudiconv is not perfect! Heuristic file will also need to be updated if your dataset has different protocols for different participants. Any custom post-hoc changes / fixes your make to BIDS datasets must be added to proc_tracker.csv under "notes" column. 
           - Example issue: heudiconv adds mysterious suffix - possibly due to how dcm2nix handles multi-echo conversion see [neurostar issue](https://neurostars.org/t/heudiconv-adding-unspecified-suffix/21450/3) 


