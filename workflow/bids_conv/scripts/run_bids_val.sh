#!/bin/bash

if [ "$#" -ne 2 ]; then
   echo "Please provide paths to the bids_dir and log_dir"
   exit 1
fi

BIDS_DIR=$1
LOG_DIR=$2
LOG_FILE=$LOG_DIR/bids_val.log
CURRENT_DIR=$PWD

/opt/bin/singularity run -B $BIDS_DIR:/data:ro /data/pd/qpn/containers/bids_validator.sif /data --verbose > $LOG_FILE

echo ""
echo "number of BIDS validation errors: `cat $LOG_FILE | grep "ERR" | wc -l`"
cat $LOG_FILE | grep "ERR"

echo ""
echo "number of subjects with BIDS validation errors, not counting bvec bval mismatch related dwi issues: `cat $LOG_FILE | grep "Evidence: sub" | grep nii.gz | cut -d " " -f2 | cut -d "_" -f1 | cut -d "-" -f2  | uniq -c | wc -l`"
cat $LOG_FILE | grep "Evidence: sub" | grep nii.gz | cut -d " " -f2 | cut -d "_" -f1 | cut -d "-" -f2  | uniq -c

echo ""
echo "number of subjects with multiple runs: `find $BIDS_DIR -name "*run-2*" | cut -d "/" -f6 | uniq -c | wc -l` (see $LOG_DIR/subjects_with_multiple_runs.txt)"

#note don't have to search for run-3, run-4 etc because those subjects will also have run-2!
find $BIDS_DIR -name "*run-2*" | cut -d "/" -f6 | uniq -c > $LOG_DIR/subjects_with_multiple_runs.txt

# subjects missing IntendedFor in fmaps
cd $BIDS_DIR
for i in sub-*; do echo $i `cat ${i}/ses-01/fmap/${i}_ses-01_acq-bold_run-1_phasediff.json | grep IntendedFor | wc -l`; done > $CURRENT_DIR/$LOG_DIR/subjects_with_missing_IntendedFor.txt
cd $CURRENT_DIR

echo ""
echo "number of subjects missing IntendedFor in fmaps: `cat $LOG_DIR/subjects_with_missing_IntendedFor.txt | grep " 0" | wc -l` (see $LOG_DIR/subjects_with_missing_IntendedFor.txt)"
cat $LOG_DIR/subjects_with_missing_IntendedFor.txt | grep " 0" | wc -l > $LOG_DIR/subjects_with_missing_IntendedFor.txt

echo ""
echo "Note: Check verbose log and lists of bids fail subjects here: $LOG_DIR"
echo "Note: BIDS validation fails and subjects with multiple runs are to be moved to /data/pd/qpn/bids_issues for further checks"
