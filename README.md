# mr_proc (Updating and testing wiht PPMI_20220210 dataset.)
Process long and prosper

## Notes
1. Principles of this MRI-preproc pipeline:
    1.  Need to define clear preproc-stages/steps;
    2.  Need to have unit/subject level of testing code;
    3.  Need to validate the dicom info from dataset and that from download info table. -> need a tab_data folder
3. Need to define clear preproc-stages/steps;

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
1. Ross's Python interface for working with Parkinson's Progression Markers Initiative (PPMI) data [pypmi](https://github.com/rmarkello/pypmi);
