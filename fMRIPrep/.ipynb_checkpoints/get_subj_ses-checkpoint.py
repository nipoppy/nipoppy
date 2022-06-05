#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: Vincent (Qing Wang)
# @Date:   2022-4-27 12:00:00
"""
======================================================
Get dataset subject session list (PPMI) for fMRIPrep preproc:
Input  dataset folder structure: PPMI_BIDS

Output file:  folder structure: ppmi_subject_session.csv
======================================================
"""
# libs and envs
import sys
# codes_dir_str='/scratch/mr_proc' # run on CC
codes_dir_str='/data/pd/ppmi/mr_proc' # run on BIC
sys.path.append(codes_dir_str)
from pathlib import Path
import pandas as pd
import numpy as np

# main PATH
codes_dir    = Path(codes_dir_str)
bids_dir_str = '/data/pd/ppmi/PPMI_BIDS' # PPMI_BIDS on BIC
# bids_dir_str = '/scratch/PPMI_BIDS' # PPMI_BIDS on CC
bids_dir     = Path(bids_dir_str)
fmriprep_dir = codes_dir / 'fMRIPrep' 

# output subject session list 
ppmi_subj_ses_file   = fmriprep_dir / 'ppmi_subject_session.csv'  # Information from download database.

from bids import BIDSLayout
ppmi_layout=BIDSLayout(bids_dir)
ppmi_layout.get_sessions()

suffix    = 'T1w'
extension = 'nii.gz'
ppmi_file_list=ppmi_layout.get(suffix=suffix, extension=extension, return_type='file')
ppmi_file_names=[x.split('/')[-1] for x in ppmi_file_list]

subj_ses_df = pd.DataFrame({'subject':[x.split('_')[0] for x in ppmi_file_names], 'session': [x.split('_')[1].split('-')[-1] for x in ppmi_file_names]}).drop_duplicates()

# Generate subject,session file for fMRIPrep preporocessing 
subj_ses_df.to_csv(ppmi_subj_ses_file, header=False, index=False)
