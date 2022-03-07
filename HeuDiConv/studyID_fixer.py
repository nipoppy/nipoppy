#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: Vincent (Qing Wang)
# @Date:   2021-7-12 12:00:00
"""
======================================================
Using correcting the inconsistent studyUIDs of dicom files, if there are any, change them to match the first one.
Adapted by Qing Wang (Vincent) from https://github.com/nipy/heudiconv/issues/280.
======================================================
"""
import pydicom
import glob

def get_args():
    import argparse
    parser = argparse.ArgumentParser(description='Input of pamameters: ')
    parser.add_argument('--data', type=str, default = 'data')
    args = parser.parse_args()
    return args

def main(DATA_DIR):
    """Entry point"""
    """1. input images"""
    if DATA_DIR=='PPMI':
        alldcm = glob.glob(DATA_DIR + '/*/*/*/*/*.dcm')
    elif DATA_DIR=='ADNI':
        alldcm = glob.glob(DATA_DIR + '/*/*/*/*/*.dcm')
    else:
        alldcm = glob.glob(DATA_DIR + '/*/*/*/*/*.dcm')
    for jj in range(0,len(alldcm)):
        ds = pydicom.dcmread(alldcm[jj])
        if jj == 0:
            studyUID = ds.StudyInstanceUID
        if ds.StudyInstanceUID != studyUID:
            print('studyUID conflict detected from ', alldcm[jj])
            ds.StudyInstanceUID = studyUID
            ds.save_as(alldcm[jj])
    return 1

if __name__ == '__main__':
    args=get_args()
    DATA_DIR=args.data;    
    print("The input data folder: ", DATA_DIR, type(DATA_DIR))
    main(DATA_DIR)
