# PPMI_processing

Repository for PPMI image processing codebase. All the imaging data were downloaded from [PPMI](https://www.ppmi-info.org/), mainly supporting 2 projects:

1. PD subtypying and progression, the corresponding version is **ver-sdMRI**, this is the base version dataset;
2. PD bio-marker reproducibility study, the corresponding version is  [**ver-livingpark**](https://github.com/LivingPark-MRI), all the data in this study but not in **ver-sdMRI** are placed here;
3. All the other versions will be created upon the creations and approvals of new PD related projects.

## Meatadata (needs to be updated)
The participant.csv. 

## Modalities and protocols
PPMI is a multi-model multi-site imaging collection, we only focus on structrual MRI (T1) and dissuion MRI (DWI). Due to the multi-site nature of PPMI, the protocols used in this data set is complex, and we manage these protocols with a [heuristic file]([HeuDiConv/Heuristics_PPMI_all.py](https://github.com/neurodatascience/mr_proc/blob/fa21c6803a5b11d7da8c0124d11f9fdeac813e79/HeuDiConv/Heuristics_PPMI_all.py)) for our dicoms to bids conversion, refer to [PPMI docs](https://www.ppmi-info.org/study-design/research-documents-and-sops) for detailed acquisition parameters.

## Processing Steps

**1. Datadownload and curation**

1.1. The dataset were downloaded from PPMI imaging collections, and located in ```/data/pd/ppmi/downloads``` on BIC server;

1.2 The dataset includes: a) The imaging data (raw file, the dicom images); 2) The downloading meta data (tsv file, metadata for this download); 3) The imaging metadata (zip file of xml files, descripters for all images); 4) The study data (demographics data, clinical assessments, etc.).

**Issues**

We also have an automatic downloading piepline from livingPark project: [ppmi-scraper](https://github.com/LivingPark-MRI/ppmi-scraper) for automatic subject level download, but the downloading meta data is not avalible. 

**2. BIDS conversion using [HeuDiConv](https://github.com/nipy/heudiconv) ver-0.9.0**

2.1 **Fix the potnetial studyID conflicts** in dicoms with [studyID_fixer](HeuDiConv/studyID_fixer.py);

Example: ```python studyID_fixer.py --data PPMI``` (parameters: dataset)

2.2 **Reorganize dicom folders** to ```PPMI/sub/session/images/*.dcm``` with [HeuDiConv/reorganize_session.py] according to the downloading meta data table;

Example: ```python reorganize_session.py --data PPMI --tab PPMI_3T_sdMRI_3_07_2022.csv``` (parameters: dataset, downloading meta data table)

2.3 **Heudiconv Run_1** to enlist all the scans and protocols: [heudiconv_run1.sh](HeuDiConv/heudiconv_run1.sh)

Example: ```./heudiconv_run1.sh PPMI sge Y``` (parameters: dataset, HPC system, whether to clear existing folder)

2.4 **Heudiconv Run_2** to create NIFTI files in BIDS format: [heudiconv_run2.sh](HeuDiConv/heudiconv_run2.sh)

Example: ```./heudiconv_run2.sh PPMI sge T1``` (parameters: dataset, HPC system, heuristics file to use all/T1)

2.5 **Heuristics files**:

[PPMI_all images](HeuDiConv/Heuristics_PPMI_all.py)

[PPMI_T1 only](HeuDiConv/Heuristics_PPMI_T1.py)

**X** Will run BIDS validator run_bids_val.sh - this uses Singularity image created from Docker validator [have not ran by now]

**Issues**

The failed conversions are here: [failed conversions](HeuDiConv/err_subjects_conversion.txt)

**3. Structural image processing using [fMRIPrep](https://github.com/nipreps/fmriprep) ver-20.2.7**

3.1 Generate the subject-session file for fMRIPrep preprocessing like ```ppmi_subject_session.csv, sdMRI_subject_session_rerun1.csv``` and the bids filter for the specific session like ```anat_ses-0.json```, tests and experiemnts in ```fMRIPrep_help.ipynb``` and run ```get_subj_ses.py``` on server;

3.2  Run anatomical only processing of fMRIPrep with **fmriprep_anat_sub.sh**;

Dataset level preproc example: ```./fmriprep_anat_sub.sh PPMI Y ppmi_subject_session.csv``` (parameters: dataset, whether to clear existing folder, subject-session table)

Subject level preproc example: ```./fmriprep_anat_sub.sh PPMI Y sub-xxxx 0``` (parameters: dataset, whether to clear existing folder, subject id, session id)

3.3  Currate results after preproc finsihed with **fmriprep_anat.format**, all the preprossed results will be zipped in 2 files (fmriprep, freesurfer) for easier data transfer.

Example: ```./fmriprep_anat.format PPMI 0 20.2.7``` (parameters: dataset, session id, fMRIPrep version)

**Issues**

1. The failed subjects are listed in [sdMRI_subject_session_rerun1](fMRIPrep/sdMRI_subject_session_rerun1.csv), rerun finished;
2. A simple QC script is created to check the output files in [fmriprep_simple_qc.py](workflow/fMRIPrep/fmriprep_simple_qc.py), it returns a rerun2 list [sdMRI_subject_session_rerun2.csv](workflow/fMRIPrep/sdMRI_subject_session_rerun2.csv), detailed QC report is stored in ```mr_proc/workflow/fMRIPrep/PPMI_ses-<session number>_fmriprep_anat_20.2.7_report.csv```;
3. Rerun2 is running on CC.

**4. Diffusion image processing using [TractoFlow](https://github.com/scilus/tractoflow) ver-???**

Note done yet.

**Issues**

## Resources and references

1. Ross's Python interface for working with Parkinson's Progression Markers Initiative (PPMI) data [pypmi](https://github.com/rmarkello/pypmi);
2. [MRIQC](https://mriqc.readthedocs.io/en/stable/)
3. [TractoFlow](https://github.com/scilus/tractoflow)
4. [SPM](https://www.fil.ion.ucl.ac.uk/spm/)
5. [MAGeT Brain](https://github.com/CoBrALab/MAGeTbrain)
