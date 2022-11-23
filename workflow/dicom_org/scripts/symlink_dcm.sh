#!/bin/bash

# This is a script to symlink a batch of subjects from /data/dicom to a project level dicom dir.
# subject list should contain PSCIDs obtained from LORIS
# e.g.: /data/dicom --> /data/pd/qpn/dicom

# author: nikhil153
# date: 12 April 2022

if [ "$#" -ne 3 ]; then
  echo "Please provide DICOM_SOURCE_DIR, DICOM_DEST_DIR, and SUBJECT_LIST"
  exit 1
fi

DICOM_SOURCE_DIR=$1
DICOM_DEST_DIR=$2
SUBJECT_LIST=$3

SUBJECT_LIST_DIR=`dirname "$SUBJECT_LIST"`
HEUDICONV_PARTICIPANT_LIST="${SUBJECT_LIST_DIR}/heudiconv_participant_list.txt"
touch ${HEUDICONV_PARTICIPANT_LIST}
chmod 775 ${HEUDICONV_PARTICIPANT_LIST}

N_SUBS=`cat $SUBJECT_LIST | wc -l`
echo "Number of subjects in the batch: $N_SUBS"
echo ""
echo "Symlinking dicom dirs from $DICOM_SOURCE_DIR to $DICOM_DEST_DIR"
echo ""

for sub in `cat $SUBJECT_LIST`; do 
   i=`ls ${DICOM_SOURCE_DIR} | grep ${sub}`
   n_matches=`echo "$i" | tr ' ' '\n' | wc -l`
   echo "number of dicom matches: $n_matches for subject $sub"
   if [[ "$i" == "" ]]; then
      echo "No scan match found for $sub in the source dir"
   else
      if [[ $n_matches > 1 ]]; then
         echo "Multiple ($n_matches) scan matches found for $sub in the source dir"
         min_size=0
         for j in `echo "$i" | tr ' ' '\n'`; do
            new_size=`ls ${DICOM_SOURCE_DIR}/${j} | wc -l`
            if [[ $new_size > $min_size ]]; then
               min_size=$new_size
               f_link=$j
            fi
         done
         echo "linking $f_link"
         i=$f_link
      fi

      PSCID=`echo $i | cut -d "_" -f1`
      DCCID=`echo $i | cut -d "_" -f2`
      BIDS_ID="${PSCID}D${DCCID}"
      echo "subject_id: $sub, dicom_file: $i, bids_id: $BIDS_ID"
   
      ln -s ${DICOM_SOURCE_DIR}/${i} $DICOM_DEST_DIR/${BIDS_ID}
      echo $BIDS_ID >> ${HEUDICONV_PARTICIPANT_LIST}
   fi
done
echo ""
echo "Symlinking complete"
echo "HeuDiConv participant list: ${HEUDICONV_PARTICIPANT_LIST}"
