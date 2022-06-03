#!/bin/bash

# This is a script to setup directory tree for mr_proc 
# author: nikhil153
# date: 1 Jun 2022

if [ "$#" -ne 2 ]; then
    echo "Please specify root dir and dataset name for your mr_proc workflow"
    exit 1
fi

LOCAL_ROOT=$1
DATASET=$2

MR_PROC_ROOT=$1/$2

if [ -d $MR_PROC_ROOT ]; then
    echo "mr_proc root dir: $MR_PROC_ROOT already exists"
    exit 1

else
    echo "setting mr_proc root dir at: $MR_PROC_ROOT"

    mkdir -p $MR_PROC_ROOT/{scratch,backups,downloads,proc,test_data,clinical,dicom,bids,derivatives,releases}
    mkdir -p $MR_PROC_ROOT/proc/{containers,envs}
    mkdir -p $MR_PROC_ROOT/test_data/{dicom,bids,derivatives}
    mkdir -p $MR_PROC_ROOT/clinical/{demographics,assessments}
    mkdir -p $MR_PROC_ROOT/derivatives/{fmriprep,tractoflow}

fi
