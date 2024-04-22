#!/bin/bash
#
#$ -cwd
#$ -o logs/FC_out.log
#$ -e logs/FC_err.log
#$ -m e
#$ -l h_rt=24:00:00
#$ -l h_vmem=32G
#$ -q origami.q

#$ -t 1-10

# TODO replace with local paths
source "</path/to/nipoppy_env>"

SUBJECT_LIST="</path/to/subject_list>"
SESSION_ID="01"
GLOBAL_CONFIG="/path/to/global_configs.json"
FC_CONFIG="/path/to/FC_config.json"

echo "Number subjects found: `cat $SUBJECT_LIST | wc -l`"

SUBJECT_ID=`sed -n "${SGE_TASK_ID}p" $SUBJECT_LIST`
echo "Subject ID: $SUBJECT_ID"
	
python "<>/run_FC.py" \
--global_config $GLOBAL_CONFIG \
--FC_config $FC_CONFIG \
--participant_id sub-$SUBJECT_ID \
--session_id $SESSION_ID