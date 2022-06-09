# PPMI_processing

Repository for PPMI image processing codebase. All the imaging data were downloaded from [PPMI](https://www.ppmi-info.org/), mainly supporting 2 projects:

1. PD subtypying and progression, the corresponding version is **ver-sdMRI**, this is the base version dataset;
2. PD bio-marker reproducibility study, the corresponding version is  [**ver-livingpark**](https://github.com/LivingPark-MRI), all the data in this study but not in **ver-sdMRI** are placed here;
3. All the other versions will be created upon the creations and approvals of new PD related projects.

## Meatadata
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

2.1 Fix the potnetial studyID conflicts in dicoms with []();

2.2 Reorganize dicom folders to ```PPMI/sub/session/images/*.dcm``` with [HeuDiConv/reorganize_session.py]

2.3 Heudiconv Run_1 to enlist all the scans and protocols: heudiconv_run1.sh
Example cmd: ```./heudiconv_run1.sh PD* 01 2018```

2.4 Heudiconv Run_2 to create NIFTI files in BIDS format: heudiconv_run2.sh
BIDS validator run_bids_val.sh - this uses Singularity image created from Docker validator

Manual update of heurisitic file using the enlisted protocols from Run_1: Heuristics_qpn.py
Heudiconv Run_2 to create NIFTI files in BIDS format: heudiconv_run2.sh
BIDS validator run_bids_val.sh - this uses Singularity image created from Docker validator
Checks for errors (ignores dwi related bval and bvec errors since they are not relevant to TractoFlow)
Checks for subjects with repeat / multiple runs for a same modality/suffix.
Checks if IntendedFor field is present in fmaps.


**Issues**

**3. Structural image processing using [fMRIPrep](https://github.com/nipreps/fmriprep) ver-20.2.7**

**Issues**

**4. Diffusion image processing using [TractoFlow](https://github.com/scilus/tractoflow) ver-???**

Note done yet.

**Issues**

## Resources and references

1. Ross's Python interface for working with Parkinson's Progression Markers Initiative (PPMI) data [pypmi](https://github.com/rmarkello/pypmi);
2. 
    1. Prepare data: including check and fix the studyID problems with ```HeuDiConv/studyID_fixer.py```;
    2. Run1: HeuDiConv_0.9.0
        1. It has run1 and run2, there should be some summary statistics and exploration for heuristics after run1 before run2, and it should be compared with the download information for validations;
        2. prepare env: 1)in_files, 2)variables, 3)folders;
        3. submit slurm jobs;
        4. collect results: 1)outputs; 2)logs;
    3. Run2: fMRIPrep_20.2.7
        1. prepare env: 1)in_files, 2)variables, 3)folders;
        2. submit slurm jobs;
        3. collect results: 1)outputs; 2)logs;
4. BIDS conventions
    1. field map: fieldmap
    2. directions: dir-
    3. magnitude map: epi
5. tbd 

## References

