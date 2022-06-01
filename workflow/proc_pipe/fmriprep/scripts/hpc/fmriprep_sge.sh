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

subject_list=$1
bids_dir="/data/pd/qpn/bids/"
fmriprep_dir="/data/pd/qpn/fmriprep/v20.2.7/"

echo "bids_dir: $bids_dir"
echo "fmriprep_dir: $fmriprep_dir"
echo "Number subjects found: `cat $subject_list | wc -l`"

subject_id=`sed -n "${SGE_TASK_ID}p" $subject_list`
echo "Subject ID: $subject_id"
	
./fmriprep_anat_and_func_sub_regular_20.2.7.sh /data/pd/qpn/bids /data/pd/qpn/fmriprep/v20.2.7/ $subject_id
