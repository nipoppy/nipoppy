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

DATASET_ROOT=$1/$2

N_ERRORS=0
N_WARNINGS=0

#########

echo "Checking mr_proc root dir ..."
if [ -d $DATASET_ROOT ]; then
    echo "  mr_proc root dir: $DATASET_ROOT exists"
else
    echo "  ERRORS: mr_proc root dir: $DATASET_ROOT is MISSING!"
    N_ERRORS=$((N_ERRORS + 1))
fi

echo ""
echo "Checking level-1 subdirs ..."
for i in {scratch,backups,downloads,proc,test_data,tabular,dicom,bids,derivatives,releases}; do
    if [ -d $DATASET_ROOT/$i ]; then
        echo "  $DATASET_ROOT/$i exists"
    else    
        echo "  ERRORS: $DATASET_ROOT/$i is MISSING!"
        N_ERRORS=$((N_ERRORS + 1))
    fi;

done

#########

echo ""
echo "Checking participants list..."

mr_proc_manifest=$DATASET_ROOT/tabular/demographics/mr_proc_manifest.csv
if [ -f $mr_proc_manifest ]; then
    echo "  mr_proc_manifest.csv exists"

    N_PARTICIPANTS=`cat $mr_proc_manifest | wc -l`
    #ignore header
    N_PARTICIPANTS=$((N_PARTICIPANTS - 1))

    N_BIDS_EXPECT_PARTICIPANTS=`cat $mr_proc_manifest | grep "sub-" | wc -l`

    echo "  number of all participants in participant list: $N_PARTICIPANTS"
    echo "  number of expected imaging participants in participant list: $N_BIDS_EXPECT_PARTICIPANTS"

    if [ $N_PARTICIPANTS -ne $N_BIDS_EXPECT_PARTICIPANTS ]; then
        echo "  WARNING: number of total and BIDS particiants are not equal!"
        N_WARNINGS=$((N_WARNINGS + 1))
    fi

else    
    N_PARTICIPANTS=0
    N_BIDS_EXPECT_PARTICIPANTS=0
    echo "  ERROR: mr_proc_manifest.csv is MISSING! Please add it inside $DATASET_ROOT/tabular/demographics/"
    N_ERRORS=$((N_ERRORS + 1))
fi

#########

echo ""
echo "Checking available test data..."

N_DICOMS=`ls $DATASET_ROOT/test_data/dicom | wc -l`

if [ -f $DATASET_ROOT/test_data/bids/participants.tsv ]; then
    N_BIDS=`cat $DATASET_ROOT/test_data/bids/participants.tsv | wc -l`
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

N_DICOMS=`ls $DATASET_ROOT/dicom | wc -l`

# Note bids creates participants.tsv and not csv
if [ -f $DATASET_ROOT/bids/participants.tsv ]; then
    N_BIDS=`cat $DATASET_ROOT/bids/participants.tsv | wc -l`
    #ignore header
    N_BIDS=$((N_BIDS - 1))
else
    N_BIDS=0
fi

echo "  number of dicoms scan dirs: $N_DICOMS"
echo "  number of bids subject dirs: $N_BIDS"

if [ $N_BIDS -ne $N_BIDS_EXPECT_PARTICIPANTS ]; then
    echo "  ERROR: number of expected and available BIDS participants do no match!"
    N_ERRORS=$((N_ERRORS + 1))
fi

#########

echo ""
echo "Checking processing pipelines to be run..."

if [ -d $DATASET_ROOT/derivatives ]; then
    PROC_PIPES=`ls $DATASET_ROOT/derivatives`
    echo "$PROC_PIPES"
    echo ""
    echo "checking if processing status file exists"
    for proc_pipe in $PROC_PIPES; do 
        if [ -f $DATASET_ROOT/derivatives/$proc_pipe/proc_status.csv ]; then
            echo "  proc status file for $proc_pipe exists"
        else
            echo "  WARNING: proc status file for $proc_pipe MISSING"
            N_WARNINGS=$((N_WARNINGS + 1))
        fi
    done 
else
    echo "  WARNING: No processing pipelines found since derivatives subdir is MISSING"
fi

echo ""
echo "Number of errors found: $N_ERRORS"
echo "Number of warnings found: $N_WARNINGS"
