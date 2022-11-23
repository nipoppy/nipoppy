#!/bin/bash

if [ "$#" -ne 2 ]; then
   echo "Provide path to dataset_dicom_dir and new_subject_list"
   exit 1
fi

DATASET_DICOM_DIR=$1
SUBJECT_LIST=$2

if [ ! -d "$DATASET_DICOM_DIR" ]; then
   echo "Could not find $DATASET_DICOM_DIR"
   echo ""
fi

N_SUBS=`cat $SUBJECT_LIST | wc -l`
echo "Number of new subjects: $N_SUBS"
echo ""

# find mri
for i in `cat $SUBJECT_LIST`; do
   echo "Searching for: $i"
   DICOM_NAME=`find_mri $i | grep "/data/dicom/${i}" | grep "found" | cut -d " " -f3`
   find_mri -claim -noconfir $DICOM_NAME 
   cp -r ${DICOM_NAME} ${DATASET_DICOM_DIR}/
   chmod -R 775 ${DATASET_DICOM_DIR}/${i}* 
done

echo "Dicom transfer complete"

