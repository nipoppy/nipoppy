#!/bin/bash

if [ "$#" -ne 4 ]; then
  echo "Please provide BIDS_DIR, SES_DIR, MODALITY, and N_ECHO"
  echo "Note that modaity can be either:"
  echo "    1) MEGRE --> swaps order of echo and part keys"
  echo "    2) PDT2 --> renames MESE to T2w and PDw" # TODO
  echo ""
  echo "e.g.: ./fix_heudiconv_naming.sh ../../tmp/heudiconv/ ses-01 MEGRE 10"
  exit 1
fi

BIDS_DIR=$1
SES_DIR=$2
MODALITY=$3
N_ECHO=$4

N_SUBS=`ls $BIDS_DIR | grep sub | wc -l`

echo "Starting to fix file names for $MODALITY (n_echo: $N_ECHO) for $N_SUBS subjects"

SUB_LIST=`ls $BIDS_DIR | grep sub`

for j in $SUB_LIST
do 
    echo "Subject id: $j";
    
    for i in $(seq 1 $N_ECHO)
    do
        # nii,mag
        mv $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_part-mag_echo-${i}_MEGRE.nii.gz  \
           $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_echo-${i}_part-mag_MEGRE.nii.gz 
        # nii,phase
        mv $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_part-phase_echo-${i}_MEGRE.nii.gz  \
           $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_echo-${i}_part-phase_MEGRE.nii.gz 
        # json,mag
        mv $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_part-mag_echo-${i}_MEGRE.json  \
           $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_echo-${i}_part-mag_MEGRE.json 
        # json,phase
        mv $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_part-phase_echo-${i}_MEGRE.json  \
           $BIDS_DIR/$j/$SES_DIR/anat/${j}_${SES_DIR}_run-1_echo-${i}_part-phase_MEGRE.json 

        # Fix the image list (only nii.gz) from "sub-<>_ses-<>_scans.tsv"
        filename=$BIDS_DIR/$j/$SES_DIR/${j}_${SES_DIR}_scans.tsv

        # replace mag files
        search="${j}_${SES_DIR}_run-1_part-mag_echo-${i}_MEGRE.nii.gz"
        replace="${j}_${SES_DIR}_run-1_echo-${i}_part-mag_MEGRE.nii.gz"
        sed -i "s/$search/$replace/" $filename

        # replace phase files
        search="${j}_${SES_DIR}_run-1_part-phase_echo-${i}_MEGRE.nii.gz"
        replace="${j}_${SES_DIR}_run-1_echo-${i}_part-phase_MEGRE.nii.gz"
        sed -i "s/$search/$replace/" $filename

    done;
done

echo "Name fixing complete"
