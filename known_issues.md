## List of issues, notes, and resolutions. 

### DICOM
- We now need a custom script to "claim" dicoms on BIC server before downloading them locally
- Some participants have multiple dicom dirs for same session (most likely from issues during scanning)
  - Heuristic filter: select dicom_dir with most files 
- Some dicoms are now "tarred" on bic server and need to be extracted before reorganizing
- Some dicoms do not have `visit` / `session` info in the filename (i.e. `MRI01`)
  - Cross-ref date with recruitment spreadsheet for identifying sessions
- Some dicoms have `derived` tag in the header 
  - These are excluded from symlinking from `raw_dicom` to `dicom` before bids conversion

### BIDS
- `dwi` error on volume count for all participants. See [neurostars issue](https://neurostars.org/t/bids-validator-volume-count-mismatch-error-for-dwi-run-with-1-direction/22508) 
- `fmap` sidecars for `PA` direction (e.g. `sub-<>_ses-<>_acq-bold_dir-PA_run-1_epi.json`) have wrong `PhaseEncodingDirection` for some participants. This will fail the downastream fmriprep processing at SDC stage. 
  - List of participant ids: `PD00296`,`PD00869`,`PD01090`,`PD01165`,`PD01232`,`PD01306`,`PD01360`,`PD01435`,`PD01551`,`PD01753`
  - This is manually changed from `i` --> `j` 

### proc_pipes
#### fmriprep
- `fmap` sidecars have wrong `PhaseEncodingDirection` for some participants. This will cause failure of fmriprep processing at SDC stage. 