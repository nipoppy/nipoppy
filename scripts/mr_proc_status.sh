#!/bin/bash

# This is a script to check directory tree status for mr_proc 
# author: nikhil153
# date: 1 Jun 2022

if [ "$#" -ne 2 ]; then
    echo "Please specify root dir and dataset name for your mr_proc workflow"
    exit 1
fi

LOCAL_ROOT=$1
DATASET=$2

MR_PROC_ROOT=$1/$2

N_ERRORS=0

#########

echo "Checking mr_proc root dir ..."
if [ -d $MR_PROC_ROOT ]; then
    echo "  mr_proc root dir: $MR_PROC_ROOT exists"
else
    echo "  mr_proc root dir: $MR_PROC_ROOT is MISSING!"
    N_ERRORS=$((N_ERRORS + 1))
fi

echo ""
echo "Checking level-1 subdirs ..."
for i in {scratch,backups,downloads,proc,test_data,clinical,dicom,bids,derivatives,releases}; do
    if [ -d $MR_PROC_ROOT/$i ]; then
        echo "  $MR_PROC_ROOT/$i exists"
    else    
        echo "  $MR_PROC_ROOT/$i is MISSING!"
        N_ERRORS=$((N_ERRORS + 1))
    fi;

done

#########

echo ""
echo "Checking participants list..."

if [ -f $MR_PROC_ROOT/clinical/demographics/participants.csv ]; then
    echo "  participants.csv exists"

    N_PARTICIPANTS=`cat $MR_PROC_ROOT/clinical/demographics/participants.csv | wc -l`
    #ignore header
    N_PARTICIPANTS=$((N_PARTICIPANTS - 1))

echo "  number of participants in participant list: $N_PARTICIPANTS"

else    
    echo "  participants.csv is MISSING! Please add it inside $MR_PROC_ROOT/clinical/demographics/"
    N_ERRORS=$((N_ERRORS + 1))
fi

#########

echo ""
echo "Checking available test data..."

N_DICOMS=`ls $MR_PROC_ROOT/test_data/dicom | wc -l`

if [ -f $MR_PROC_ROOT/test_data/bids/participants.tsv ]; then
    N_BIDS=`cat $MR_PROC_ROOT/test_data/bids/participants.tsv | wc -l`
    #ignore header
    N_BIDS=$((N_BIDS - 1))
else
    N_BIDS=0
fi

echo "  number of test dicom scan dirs: $N_DICOMS"
echo "  number of test bids subject dirs: $N_BIDS"

#########

echo ""
echo "Checking available real data..."

N_DICOMS=`ls $MR_PROC_ROOT/dicom | wc -l`

# Note bids creates participants.tsv and not csv
if [ -f $MR_PROC_ROOT/bids/participants.tsv ]; then
    N_BIDS=`cat $MR_PROC_ROOT/bids/participants.tsv | wc -l`
    #ignore header
    N_BIDS=$((N_BIDS - 1))
else
    N_BIDS=0
fi

echo "  number of real dicoms scan dirs: $N_DICOMS"
echo "  number of real bids subject dirs: $N_BIDS"

#########

echo ""
echo "Checking processing pipelines to be run..."

if [ -d $MR_PROC_ROOT/derivatives ]; then
    PROC_PIPES=`ls $MR_PROC_ROOT/derivatives`
    echo "$PROC_PIPES"
else
    echo "  No processing pipelines found since derivatives subdir is MISSING"
fi

echo ""
echo "Number of errors found: $N_ERRORS"
