#!/bin/bash
#
#$ -cwd
#$ -o heudiconv_run2_out.log
#$ -e heudiconv_run2_err.log
#$ -m e
#$ -l h_rt=24:00:00
#$ -l h_vmem=32G
#$ -q origami.q

#$ -t 1-35
	
if [ "$#" -ne 1 ]; then
  echo "Please provide subject list"
  exit 1
fi

subject_list=$1
LOCAL_WD="/data/pd/qpn"
ses_id="01"

echo "Number subjects found: `cat $subject_list | wc -l`"

subject_id=`sed -n "${SGE_TASK_ID}p" $subject_list`
echo "Subject ID: $subject_id"
	
./heudiconv_run2.sh $LOCAL_WD $subject_id $ses_id Heuristics_qpn.py
