# QPN_processing
mr_proc branch for QPN image processing code

## Recruitment (imaging) and participant naming
- Recruitment updates are provided by study coordinator(s) in a Google Sheet: `QPN_Imaging_Codes.xlsx`.
- Latest LORIS participant manifest is fetched from [LORIS](https://copn.loris.ca/). 
  
## MRI acquition
### Available modalities and protocols
![QPN MR acq protocols](./images/QPN_dicom_protocols.png)

## Clinical data
- TODO

## Containers (Singularity)
- [Heudionv](https://heudiconv.readthedocs.io/en/latest/installation.html#singularity) (current version: `0.11.6`)
- [BIDS validator](https://github.com/bids-standard/bids-validator)
- [fMRIPrep](https://fmriprep.org/en/1.5.5/singularity.html) (current version: `20.2.7`)

## Global Configs
   - Create the [global_configs.json](./workflow/global_configs.json) file with paths to QPN dataset, pipeline versions, and containers used by several workflow scripts.

## Processing Steps

### DICOM (re)organization
1. [setup_dicom_refresh.py](workflow/dicom_org/setup_dicom_refresh.py)
  - The `participant_id` (i.e. `PSCID`) list is extrcted from `subj_manifest` tab from the Google Sheet: `QPN_Imaging_Codes.xlsx`. 
  - A `BIDS_ID` for each participant is then generated in this format `<PSCID>D<DCCID>` using LORIS manifest. This was done maintain 1-1 correspondance with LORIS, especially in cases when multiple DICOMs are generated for a participant during same visit.
  - The `BIDS_IDs` for the current recruited participant list is compared against `participants.csv` from the current `BIDS_DIR` in the `<QPN_DATASET_ROOT>/bids`.  
  - This generates list of new participant_ids whose DICOMs need to fetched and processed. 
2. [fetch_new_scans](workflow/dicom_org/scripts/fetch_new_scans.sh)
  - The new participants are then search in /data/dicom using BIC's new [`find_mri`](https://forum.bic.mni.mcgill.ca/t/how-to-retrieve-download-mri-dicom-data/1657) utility (Sept 2022). 
  - These participants are copied into `<QPN_DATASET_ROOT>/scratch/dicom_raw` in separate visit_wise (ses-01, ses-02, ses-unknown) sub-directories. 
3. [organize_dicoms.py](workflow/dicom_org/organize_dicoms.py) 
  - Symlinks `<QPN_DATASET_ROOT>/scratch/dicom_raw/ses-<>` into `<QPN_DATASET_ROOT>/dicom/ses-<>`.
  - The orginal DICOM dirname is now renamed to `BIDS_ID`

### BIDS conversion using [Heudiconv](https://heudiconv.readthedocs.io/en/latest/)   

1. [run_bids_conv.py](workflow/bids_conv/run_bids_conv.py)
    - Use `--stage 1` flag to enlist all the scans and protocols
    - Rename [sample_heuristic.py](workflow/bids_conv/sample_heuristic.py) to [heuristic.py](workflow/bids_conv/heuristic.py) and update according to MRI acq protocols. 
    - Use `--stage 2` flag to do the BIDS converstion based on [heuristic.py](workflow/bids_conv/heuristic.py) and update according to MRI acq protocols. 
    - Example cmd: 
       ``` 
       python run_bids_conv.py --global_config ../../global_configs.json --participant_id MNI02 --session_id 01 --stage <> 
       ```
    - You can do a test run by setting the flag `--test_run` which uses subsample from `<QPN_DATASET_ROOT>/test_data/`
    - You cand do a local batch run by using [run_bids_conv_batch.sh](workflow/bids_conv/run_bids_conv_batch.sh)

2. [run_bids_val.sh](bids/scripts/run_bids_val.sh) 
    - Checks for errors (ignores dwi related bval and bvec errors since they are not relevant to TractoFlow) 
    - Checks for subjects with repeat / multiple runs for a same modality/suffix. 
    - Checks if [IntendedFor](https://github.com/nipy/heudiconv/pull/482) field is present in fmaps.

3. Issues:
    - Filenames mismatch between Heudiconv and [BIDS BEP](https://github.com/bids-standard/bep001/blob/master/src/04-modality-specific-files/01-magnetic-resonance-imaging-data.md). Use modify [fix_heudiconv_naming.sh](bids/scripts/fix_heudiconv_naming.sh) to fix issues.
    - Heudiconv will generate two NIFTIs with PDT2 suffix with different echo index - which may not be ideal for certain pipelines which require separate PDw and T2w suffixes. 
    - ~~Heudiconv will also swap the order of "echo" and "part" for MEGRE scans.~~ (This has been fixed in the Heudiconv `v0.11.6`, which now used as a container for this processing)
    - Heudiconv adds mysterious suffix - possibly due to how dcm2nix handles multi-echo conversion see [neurostar issue](https://neurostars.org/t/heudiconv-adding-unspecified-suffix/21450/3) 
      - Examples: 1) sub-PD00509D598628_ses-01_run-3_T1w_heudiconv822a_ROI1.nii.gz 2) sub-PD00509D598628_ses-01_run-3_T1w2.nii.gz
      - Currently removing these files manually since only 3 subjects have this issue: PD00119D567297, PD00509D598628, PD00435D874573

### Structural and functional image processing 
#### [fMRIPrep](https://fmriprep.org/en/stable/)
1. [run_fmriprep.py](workflow/proc_pipe/fmriprep/run_fmriprep.py)
  - Mandatory: For FreeSurfer tasks, **you need to have a [license.txt](https://surfer.nmr.mgh.harvard.edu/fswiki/License) file inside `<QPN_DATASET_ROOT>/derivatives/fmriprep`**
  - Mandatory: fMRIPrep manages brain-template spaces using [TemplateFlow](https://fmriprep.org/en/stable/spaces.html). These templates can be shared across studies and datasets. Use [global configs](./workflow/global_configs.json) to specify path to `TEMPLATEFLOW_DIR` where these templates can reside. For machines with Internet connections, all required templates are automatically downloaded duing the fMRIPrep run. 
  - You can run "anatomical only" workflow by adding `--anat_only` flag
  - Copy and rename [sample_bids_filter.json](workflow/proc_pipe/fmriprep/sample_bids_filter.json) as [bids_filter.json](workflow/proc_pipe/fmriprep/bids_filter.json). 
  - Note: when `--use_bids_filter` flag is set, this `bids_filter.json` automatically gets copied into `<DATASET_ROOT>/bids/bids_filter.json` to be seen by the Singularity container.
  - For QPN you need to use this file to ignore neuromelanin scans (i.e. `sub-<>_acq-NM_run-1_T1w.nii.gz`) during regular anatomical workflow.
  - Similar to HeuDiConv, you can do a test run by adding `--test_run` flag. (Requires a BIDS participant directory inside `<DATASET_ROOT>/test_data/bids`)
  - Example command:
    ``` 
    python run_fmriprep.py --global_config ../../global_configs.json --participant_id MNI01 --session_id 01 --use_bids_filter --output_dir <origami_space>/nikhil/qpn/ 
    ```
    - You can change default run parameters in the [run_fmriprep.sh](workflow/proc_pipe/fmriprep/scripts/run_fmriprep.sh) by looking at the [documentation](https://fmriprep.org/en/stable/usage.html)

2. Issues:
  - Due to weird permissions issues on BIC Singularity cannot read from the directories created on `PD data disk` during a run. Therefore `--output_dir <origami_space>/nikhil/qpn/` must be specified in the ORIGAMI disk. 
  - Functional fmaps require `IntendedFor` field which was not populated in the older version of Heudiconv. This is now fixed in the Heudiconv commit: cb2fd91, which now used as a container for this processing)
  - There were few dicoms (~6) which had wrong `PhaseEncodingDirection` for PA epi scans after Heudiconv conversion. This is currently fixed manually by changing sidecar fmap jsons by changing (i-->j).  

#### [MRIQC](https://mriqc.readthedocs.io/en/stable/)
- TODO

#### [TractoFlow](https://github.com/scilus/tractoflow)
  - Version: tractoflow_2.2.1_b9a527_2021-04-13.sif
  - Notes:  Might need to "average" the PA acquisition, since Tractoflow assume 1 volume but there is 3 in "dwi" (Re: Etienne St-Onge 21 March 2022) 


### Useful resources:
- BIDS, fMRIPrep, MRIQC: [tutorial](https://sarenseeley.github.io/BIDS-fmriprep-MRIQC.html)
- Heudiconv: [tutorial](https://neuroimaging-core-docs.readthedocs.io/en/latest/pages/heudiconv.html)
