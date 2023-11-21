#!/bin/bash
#
#$ -cwd
#$ -o logs/FC_out.log
#$ -e logs/FC_err.log
#$ -l h_rt=24:00:00
#$ -l h_vmem=12G
#$ -q origami.q

#$ -t 1-265

source ../../../dFC/anaconda3/etc/profile.d/conda.sh
conda activate qpn_env

SUBJECT_LIST="./hpc_job_list_func_conn.txt"
SESSION_ID="01"
GLOBAL_CONFIG="../../../../pd/qpn/proc/global_configs.json"
FC_CONFIG="./FC_configs.json"

echo "Number subjects found: `cat $SUBJECT_LIST | wc -l`"

SUBJECT_ID=`sed -n "${SGE_TASK_ID}p" $SUBJECT_LIST`
echo "Subject ID: $SUBJECT_ID"
	
python "./run_FC.py" \
--global_config $GLOBAL_CONFIG \
--FC_config $FC_CONFIG \
--participant_id sub-$SUBJECT_ID \
--session_id $SESSION_ID \
--output_dir "../output"

conda deactivate