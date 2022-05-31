# QPN_processing
Repository for QPN image processing codebase

## Meatadata
- [QPN dataset V1](metadata/ID_lists/subjects/COPN_loris_imaging_subject_list_11_April_2022.csv): This is generated from subjects that are present in the [Loris instance](https://copn.loris.ca/) 
  -  These subjects serve as input to BIDS conversion and subsequent image processing pipelines
  -  The DICOMs are grabbed from BIC server (i.e. /data/pd/qpn/dicom) 
- [QPN MR image proc status](metadata/ID_lists/subjects/QPN_image_proc_status.csv): This tracks the progress of image processing pipelines e.g. Heudiconv, fmriprep etc. 

## Available modalities and protocols
![QPN MR acq protocols](./QPN_dicom_protocols.png)

## Processing Steps

### DICOM extraction and symlinks
  1. The QPN DICOMs were located in multiple directories in nested tar.gz archives. These were extracted and renamed using: [extract_dcm.sh](./bids/scripts/extract_dcm.sh). 
     - Example cmd: 
       ``` ./extract_dcm.sh path/to/DCM_*.tar /path/to/output/ ```
  2. These were then moved to BIC:data/dicom directory which is a repository for all scans acquired at BIC. The ongoing QPN scans are directly stored here by QPN data collection team. 
  3. Symlinks for QPN scans are made from /data/dicom to /data/pd/qpn/dicom which serves as a QPN specific dicom dir. 
  4. The symlinks are filtered to exlude duplicate DICOMs for a subject due to bad acquisition. These are then renamed and copied to dicom_heudiconv directory which serves as an input to BIDS conversion using heudiconv.

### BIDS conversion using [Heudiconv](https://heudiconv.readthedocs.io/en/latest/)   
  1. Heudiconv Run_1 to enlist all the scans and protocols: [heudiconv_run1.sh](/bids/scripts/heudiconv_run1.sh)
     - Example cmd: 
       ``` ./heudiconv_run1.sh PD* 01 2018 ```
  2. Manual update of heurisitic file using the enlisted protocols from Run_1: [Heuristics_qpn.py](bids/heuristics/Heuristics_qpn.py)
  3. Heudiconv Run_2 to create NIFTI files in BIDS format: [heudiconv_run2.sh](/bids/scripts/heudiconv_run2.sh)
  4. BIDS validator [run_bids_val.sh](bids/scripts/run_bids_val.sh) - this uses Singularity image created from [Docker validator](https://github.com/bids-standard/bids-validator) 
      - Checks for errors (ignores dwi related bval and bvec errors since they are not relevant to TractoFlow) 
      - Checks for subjects with repeat / multiple runs for a same modality/suffix. 
      - Checks if [IntendedFor](https://github.com/nipy/heudiconv/pull/482) field is present in fmaps.
  5. Issues:
      - Filenames mismatch between Heudiconv and [BIDS BEP](https://github.com/bids-standard/bep001/blob/master/src/04-modality-specific-files/01-magnetic-resonance-imaging-data.md). Use modify [fix_heudiconv_naming.sh](bids/scripts/fix_heudiconv_naming.sh) to fix issues.
      - Heudiconv will generate two NIFTIs with PDT2 suffix with different echo index - which may not be ideal for certain pipelines which require separate PDw and T2w suffixes. 
      - ~~Heudiconv will also swap the order of "echo" and "part" for MEGRE scans.~~ (This has been fixed in the Heudiconv commit: cb2fd91, which now used as a container for this processing)
      - Heudiconv adds mysterious suffix - possibly due to how dcm2nix handles multi-echo conversion see [neurostar issue](https://neurostars.org/t/heudiconv-adding-unspecified-suffix/21450/3) 
        - Examples: 1) sub-PD00509D598628_ses-01_run-3_T1w_heudiconv822a_ROI1.nii.gz 2) sub-PD00509D598628_ses-01_run-3_T1w2.nii.gz
        - Currently removing these files manually since only 3 subjects have this issue: PD00119D567297, PD00509D598628, PD00435D874573

### Structural and functional image processing 
#### [fMRIPrep](https://fmriprep.org/en/stable/)
  - Download / build [fmriprep Singularity](https://fmriprep.org/en/1.5.5/singularity.html) version: fmriprep_20.2.7.sif. 
  - Use [sample_bids_filter.json](fmriprep/sample_bids_filter.json) to filter sesions, runs, and suffixes. Especially we need to exclude NM T1w scans. Note that this json needs to be copied into your BIDS dir after your edit it. 
  - Run script [fmriprep_anat_and_func_sub_regular_20.2.7.sh](fmriprep/scripts/fmriprep_anat_and_func_sub_regular_20.2.7.sh) to process single subject (i.e. individual-level BIDS subdir)
     - Example cmd: 
     ```./fmriprep_anat_and_func_sub_regular_20.2.7.sh /path/to/root/bids/dir/ /path/to/output/dir/ <participant_id>```
     - Use [fmriprep_sge.sh](fmriprep/scripts/fmriprep_sge.sh) to submit cluster jobs with list of participants as csv input.
  - Issues:
     - Functional fmaps require `IntendedFor` field which was not populated in the older version of Heudiconv. This is now fixed in the Heudiconv commit: cb2fd91, which now used as a container for this processing)
     - There were few dicoms (~6) which had wrong `PhaseEncodingDirection` for PA epi scans after Heudiconv conversion. This is currently fixed manually by changing sidecar fmap jsons by changing (i-->j).  

#### [TractoFlow](https://github.com/scilus/tractoflow)
  - Version: tractoflow_2.2.1_b9a527_2021-04-13.sif
  - Notes:  Might need to "average" the PA acquisition, since Tractoflow assume 1 volume but there is 3 in "dwi" (Re: Etienne St-Onge 21 March 2022) 


### Useful resources:
- BIDS, fMRIPrep, MRIQC: [tutorial](https://sarenseeley.github.io/BIDS-fmriprep-MRIQC.html)
- Heudiconv: [tutorial](https://neuroimaging-core-docs.readthedocs.io/en/latest/pages/heudiconv.html)
