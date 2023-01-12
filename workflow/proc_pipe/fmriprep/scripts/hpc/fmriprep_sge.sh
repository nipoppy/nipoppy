#!/bin/bash
#
#$ -cwd
#$ -o fmriprep_out.log
#$ -e fmriprep_err.log
#$ -m e
#$ -l h_rt=24:00:00
#$ -l h_vmem=32G
#$ -q origami.q

#$ -t 1-8
	
if [ "$#" -ne 1 ]; then
  echo "Please provide subject list"
  exit 1
fi

SUBJECT_LIST=$1
SESSION_ID=$2
BIDS_FILTER="bids_filter.json"
DATASET_ROOT="/data/pd/qpn/"
TEST_RUN="0"

echo "DATASET_ROOT: $DATASET_ROOT"
echo "Number subjects found: `cat $SUBJECT_LIST | wc -l`"

SUBJECT_ID=`sed -n "${SGE_TASK_ID}p" $SUBJECT_LIST`
echo "Subject ID: $SUBJECT_ID"
	
./run_fmriprep_anat.sh -d $DATASET_ROOT -p $SUBJECT_ID -s $SESSION_ID -b $BIDS_FILTER -t $TEST_RUN
