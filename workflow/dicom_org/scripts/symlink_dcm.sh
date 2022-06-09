#!/bin/bash

# This is a script to symlink a batch of subjects from /data/dicom to a project level dicom dir.
# subject list should contain PSCIDs obtained from LORIS
# e.g.: /data/dicom --> /data/pd/qpn/dicom

# author: nikhil153
# date: 12 April 2022

if [ "$#" -ne 2 ]; then
  echo "Please provide subject-list-file and project-dicom-dir"
  exit 1
fi

SUBJECT_LIST=$1
PROJECT_DICOM_DIR=$2

SOURCE_DICOM_DIR="/data/dicom"
DICOM_LIST="data_dicom_matches.txt"

N_SUBS=`cat $SUBJECT_LIST | wc -l`
echo "Number of subjects in the batch: $N_SUBS"

echo "Identifying available DICOMs for the provided subject list"
for i in `cat $SUBJECT_LIST`; do ls $SOURCE_DICOM_DIR | grep `echo $i | cut -d "," -f2`; done > $DICOM_LIST

N_DICOMS=`cat $DICOM_LIST | wc -l`
echo "Number of DICOM matches in $SOURCE_DICOM_DIR: $N_DICOMS"

echo "Symlinking dicom dirs from $SOURCE_DICOM_DIR to $PROJECT_DICOM_DIR"
for i in `cat $DICOM_LIST`; do ln -s ${SOURCE_DICOM_DIR}/${i} $PROJECT_DICOM_DIR/${i}; done
echo "Symlinking complete"
