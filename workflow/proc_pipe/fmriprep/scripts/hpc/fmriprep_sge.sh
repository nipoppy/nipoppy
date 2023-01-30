#!/bin/bash
#
#$ -cwd
#$ -o ./sge_logs/
#$ -e ./sge_logs/
#$ -M nikhil.bhagwat@mcgill.ca
#$ -m a
#$ -m e
#$ -l h_rt=24:00:00
#$ -l h_vmem=32G
#$ -q origami.q

#$ -t 1-34
	
if [ "$#" -ne 1 ]; then
  echo "Please provide subject list"
  exit 1
fi

# load python env
source /data/origami/nikhil/my_envs/brain_diff/bin/activate

participant_list=$1
global_config="/data/origami/nikhil/my_repos/mr_proc/workflow/global_configs.json"
session_id="01"
output_dir="/data/origami/nikhil/qpn/"

echo "output_dir: $fmriprep_dir"
echo "Number participant found: `cat $participant_list | wc -l`"

participant_id=`sed -n "${SGE_TASK_ID}p" $participant_list`
echo "Subject ID: $participant_id"

python ../../run_fmriprep.py --global_config $global_config \
--participant_id $participant_id \
--session_id $session_id \
--use_bids_filter \
--output_dir $output_dir
