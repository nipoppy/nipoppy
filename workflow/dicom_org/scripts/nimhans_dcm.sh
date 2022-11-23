#!/bin/bash

# This is a script to rename and organize nimhans PD study dicoms into subject-specific dirctories

# author: nikhil153
# date: 12 April 2022
# /home/nimhans/scratch/nimhans_pd_study/raw_dicom/

if [ "$#" -ne 2 ]; then
  echo "Please provide subject-list-file and raw-dicom-dir"
  exit 1
fi

SUBJECT_LIST=$1
RAW_DICOM_DIR=$2

N_SUBS=`cat $SUBJECT_LIST | wc -l`
echo "Number of subjects in the batch: $N_SUBS"

