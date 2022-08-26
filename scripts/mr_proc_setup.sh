#!/bin/bash

# This is a script to setup dataset directory tree to be processed by mr_proc 
# author: nikhil153
# date: 1 Jun 2022

if [ "$#" -ne 2 ]; then
    echo "Please specify local root dir and dataset name to generate mr_proc directory structure"
    exit 1
fi

LOCAL_ROOT=$1
DATASET=$2

DATASET_ROOT=$1/$2

if [ -d $DATASET_ROOT ]; then
    echo "dataset root dir: $DATASET_ROOT already exists"
    exit 1

else
    echo "setting mr_proc root dir at: $DATASET_ROOT"

    mkdir -p $DATASET_ROOT/{scratch,backups,downloads,proc,test_data,tabular,dicom,bids,derivatives,releases}
    mkdir -p $DATASET_ROOT/proc/{containers,envs}
    mkdir -p $DATASET_ROOT/test_data/{dicom,bids,derivatives,tabular}
    mkdir -p $DATASET_ROOT/tabular/{demographics,assessments}
    mkdir -p $DATASET_ROOT/derivatives/{fmriprep,tractoflow}

fi
