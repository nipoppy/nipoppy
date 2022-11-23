#!/bin/bash

# This is a script to symlink a batch of subjects from /data/dicom to a project level dicom dir.
# subject list should contain PSCIDs obtained from LORIS
# e.g.: /data/dicom --> /data/pd/qpn/dicom

# author: nikhil153
# date: 12 April 2022

if [ "$#" -ne 3 ]; then
  echo "Please provide DICOM_SOURCE_DIR, mr_proc_dataset_root_dir, and the subject_list_file"
  exit 1
fi

DICOM_SOURCE_DIR=$1
DATASET_ROOT=$2
SUBJECT_LIST=$3

MR_PROC_DICOM_DIR="$DATASET_ROOT/dicom"

N_SUBS=`cat $SUBJECT_LIST | wc -l`
echo "Number of subjects in the batch: $N_SUBS"

echo "Symlinking dicom dirs from $DICOM_SOURCE_DIR to $MR_PROC_DICOM_DIR"
for sub in `cat $SUBJECT_LIST`; do 
   i=`ls $sub`
   PSCID=`echo $i | cut -d "_" -f1`
   DCCID=`echo $i | cut -d "_" -f2`
   BIDS_ID="${PSCID}D${DCCID}"

   ln -s ${DICOM_SOURCE_DIR}/${i} $MR_PROC_DICOM_DIR/${BIDS_ID}
done

echo "Symlinking complete"
