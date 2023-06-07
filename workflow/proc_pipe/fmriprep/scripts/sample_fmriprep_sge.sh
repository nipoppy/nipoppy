#!/bin/bash
#
#$ -cwd
#$ -o logs/fmriprep_out.log
#$ -e logs/fmriprep_err.log
#$ -m e
#$ -l h_rt=24:00:00
#$ -l h_vmem=32G
#$ -q origami.q

#$ -t 2-11

source /data/origami/nikhil/my_envs/mr_proc_env/bin/activate

SUBJECT_LIST="<>"
SESSION_ID="01"
GLOBAL_CONFIG="<>/global_configs.json"

echo "Number subjects found: `cat $SUBJECT_LIST | wc -l`"

SUBJECT_ID=`sed -n "${SGE_TASK_ID}p" $SUBJECT_LIST`
echo "Subject ID: $SUBJECT_ID"
	
python "<>/run_fmriprep.py" \
--global_config $GLOBAL_CONFIG \
--participant_id sub-$SUBJECT_ID \
--session_id $SESSION_ID \
--use_bids_filter