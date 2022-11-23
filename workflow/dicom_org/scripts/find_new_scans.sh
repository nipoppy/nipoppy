#!/bin/bash

if [ "$#" -ne 2 ]; then
   echo "Provide path to the latest QPN subject manifest CSV and release id"
   exit 1
fi

SUBJECT_MANIFEST=$1
RELEASE_ID=$2

MANIFEST_DIR=`dirname "$SUBJECT_MANIFEST"`/"$RELEASE_ID"/
if [ ! -d "$MANIFEST_DIR" ]; then
   echo "Creating ${RELEASE_ID} dir..."
   echo ""
   mkdir $MANIFEST_DIR
   chmod -R 775 $MANIFEST_DIR
fi

MANIFEST_LIST="${MANIFEST_DIR}/subject_manifest_list.txt"

BIDS_DIR="/data/pd/qpn/bids/"
BIDS_LIST="${MANIFEST_DIR}/bids_list.txt"

NEW_SUBJECTS_LIST="${MANIFEST_DIR}/new_subject_list.txt"

# Generate list of total available subjects to date
cat $SUBJECT_MANIFEST | cut -d "," -f1 | grep -v participant_id > ${MANIFEST_LIST}
N_AVAIL=`cat ${MANIFEST_LIST} | wc -l`
echo "Number of total available subjets: ${N_AVAIL}"
echo ""
chmod 775 $MANIFEST_LIST

# Identify subjects alread available in qpn/bids/
ls $BIDS_DIR | grep sub | cut -d "-" -f2 | cut -c -7 > $BIDS_LIST
N_BIDS=`cat ${BIDS_LIST} | wc -l`
echo "Number of current BIDS subjets: ${N_BIDS}"
echo ""
chmod 775 $BIDS_LIST

# Identify new subjects
grep -v -f $BIDS_LIST $MANIFEST_LIST > $NEW_SUBJECTS_LIST
chmod 775 $NEW_SUBJECTS_LIST

N_NEW_SUBS=`cat ${NEW_SUBJECTS_LIST} | wc -l`
echo "Number of new subjects: ${N_NEW_SUB}. See $NEW_SUBJECTS_LIST for the list."
echo ""

