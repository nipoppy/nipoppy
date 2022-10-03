# mr_proc 
A workflow for standarized MR images processing. 
*Process long and prosper.*

## Objective
This repo will contain container recipes and run scripts to manage MR data organization and image processing. Currently, it offers scripts to
    1. Standadized data i.e. convert DICOMs into BIDS
    2. Run commonly used image processing pipelines e.g. FreeSurfer, fMRIPrep
    
The scripts in mr_proc operate on a dataset directory with a specific subdir tree structure.

<img src="imgs/mr_proc_data_proc_org.jpg" alt="Drawing" align="middle" width="500px"/>

The organization mr_proc code module is as follows:
   - scripts: helper code to setup and check status of mr_proc
   - workflow: code modules to exectute mr_proc stages and logging
   - metadata: files to track mr_proc progress
   - notebooks: helper notebooks for data wrangling

## Workflow steps

### 0. Setup dataset directory structure
   - mr_proc expects following directory tree with several *mandatory* subdirs and files. 
   - You can run `scripts/mr_proc_setup.sh` to create this directory tree. 
   - You can run `scripts/mr_proc_stutus.sh` check status of your dataset

<img src="imgs/mr_proc_data_dir_org.jpg" alt="Drawing" align="middle" width="1000px"/>

### 1. Create subject manifest
   - Create a `participants.csv` in `<dataset>/tabular/demographics` comprising at least `participant_id`,`age`,`sex`,`group` (typically a diagnosis) columns.  
       - This list serves as a ground truth for subject availability and participant IDs are used to create BIDS ids downstream.
       
### 2. Gather MRI acquisition protocols (Optional)
   - List all the modalities and acquisition protocols used duing scanning e.g. MPRAGE, 3DT1, FLAIR, RS-FMRI etc. in the `mr_proc/workflow/dicom_org/scan_protocols.csv`
   - Although optional this is an important documentation for comparing across studies. 
   
### 3. DICOM organization
   - Scanner DICOM files are named and stored in various formats and locations. In this step we extract, copy, and rename DICOMs in a single directory for all participants with available imaging data. 
       - Copy / download all "raw dicoms"`<dataset>/scratch/raw_dicoms` directory.
       - Write a script to extract, copy, and rename these raw DICOMs into `<dataset>/dicom`. Ensure `participant_id` naming matches with `participants.csv` in `<dataset>/tabular/demographics` 
   - Copy a single participant (i.e. dicom dir) into `<dataset>/test_data/dicom`. This participant will serve as a test case for various pipelines. 
   
### 4. BIDS conversion using [Heudiconv](https://heudiconv.readthedocs.io/en/latest/) ([tutorial](https://neuroimaging-core-docs.readthedocs.io/en/latest/pages/heudiconv.html))
   - Copy Heudiconv container into: `<dataset>/proc/containers`
   - Run single participant tests: 
       - Modify and run `./heudiconv_run1.sh` with `-t 1` flag and apporpriate local path for mr_proc_dataset_dir. This will generate list of available protocols from DICOM header. This script will use a test participant from test_data/dicom for processing. 
       - sample cmd: `./heudiconv_stage_1.sh -d ~/scratch/mr_proc/<dataset> -p MNI001 -s 01 -l . -t 1` where, 
            - d: dataset_root_dir 
            - p: participant_id
            - s: session_id
            - l: symlink_datastore_dir (only needed if your dicoms are symlinks)
            - t: 1 implies a test run

       - Manually update the sample heurisitic file: `mr_proc/workflow/bids_conv/heuristic.py` using the enlisted protocols from run1. 
       - Add updated heuristic file here: `<dataset>/proc/`
       - Modify and run `./heudiconv_run2.sh` with `-t 1` flag and apporpriate local path for mr_proc_dataset_dir. This will convert the DICOMs into NIFTIs along with sidecar JSONs and organize them based on your heuristic file. The BIDS dataset is created under /test_data/bids. 
       - sample cmd: `./heudiconv_stage_2.sh -d ~/scratch/mr_proc/<dataset> -p MNI001 -s 01 -l . -t 1` where, 
            - d: dataset_root_dir 
            - p: participant_id
            - s: session_id
            - l: symlink_datastore_dir (only needed if your dicoms are symlinks)
            - t: 1 implies a test run
         
       - Run BIDS validator (see below for details). 
   - Run entire dataset (provided single participant test is successful) 
       - Modify and run `./heudiconv_stage_1.sh` and `./heudiconv_stage_2.sh` with the `-t 0` flag. This will require you to specify your real DICOM and BIDS dir paths. 
       - The above scripts are written to work for single participant (i.e. single DICOM dir). The entire dataset can be BIDSified using a "for loop" or if you have access to a cluster you can run it parallel using heudiconv_stage_<>_sge.sh or heudiconv_stage_<>_slurm.sh queue submission scripts. 

### 5. Run BIDS validator for the entire dataset.
   - Copy `bids_validator.sif` container into `<dataset>/proc/containers`
   - Run `run_bids_val.sh <bids_dir> <log_dir>` to check for errors and warnings
        - Alternatively if your machine has a browser you can also use an online [validator](https://bids-standard.github.io/bids-validator/)
   - Note that Heudiconv is not perfect! Common issues:
       - Make sure you match the version of Heudiconv and BIDS validator standard. 
       - Heuristic file will also need to be updated if your dataset has different protocols for different participants. 
       - You should also open an issue on this repo with the problems and solutions you encounter during processing. 
       
### 6. Run processing pipelines
Curating dataset into BIDS format simplifies running several commonly used pipelines. Each pipeline follows similar steps:
   - Specify pipeline container (i.e. Singularity image / recipe) 
   - Run single participant test. This uses sample participant from /test_data/bids as input and generates output in the /test_data/<pipeline> dir. 
   - Run entire dataset (provided single participant test is successful)

#### [fMRIPrep](https://fmriprep.org/en/stable/) (including FreeSurfer) 

#### [MRIQC](https://mriqc.readthedocs.io/en/stable/)

#### [SPM](https://www.fil.ion.ucl.ac.uk/spm/)

#### [TractoFlow](https://github.com/scilus/tractoflow)

#### [MAGeT Brain](https://github.com/CoBrALab/MAGeTbrain)
