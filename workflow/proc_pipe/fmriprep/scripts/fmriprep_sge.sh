#!/bin/bash
#
#$ -cwd
#$ -o logs/fmriprep_qpn_sandbox_out.log
#$ -e logs/fmriprep_qpn_sandbox_err.log
#$ -m e
#$ -l h_rt=24:00:00
#$ -l h_vmem=32G
#$ -q origami.q

#$ -t 2-11

source /data/origami/nikhil/my_envs/mr_proc_env/bin/activate

SUBJECT_LIST="/data/origami/nikhil/datasets/sandbox/qpn/tabular/participants_reprocess_ids.txt"
SESSION_ID="01"
GLOBAL_CONFIG="/data/origami/nikhil/datasets/sandbox/qpn/proc/global_configs.json"

echo "Number subjects found: `cat $SUBJECT_LIST | wc -l`"

SUBJECT_ID=`sed -n "${SGE_TASK_ID}p" $SUBJECT_LIST`
echo "Subject ID: $SUBJECT_ID"
	
python /data/origami/nikhil/my_repos/mr_proc-qpn/workflow/proc_pipe/fmriprep/run_fmriprep.py \
--global_config $GLOBAL_CONFIG \
--participant_id sub-$SUBJECT_ID \
--session_id $SESSION_ID \
--use_bids_filter
