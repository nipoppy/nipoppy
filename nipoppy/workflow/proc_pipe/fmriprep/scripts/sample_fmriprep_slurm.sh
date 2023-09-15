#!/bin/bash

#SBATCH -J fmriprep_test_run
#SBATCH --time=23:00:00
#SBATCH --account=<>
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=8G
# Outputs ----------------------------------
#SBATCH -o ./slurm_logs/%x-%A-%a_%j.out
#SBATCH -e ./slurm_logs/%x-%A-%a_%j.err
#SBATCH --mail-user=<>
#SBATCH --mail-type=ALL
# ------------------------------------------

#SBATCH --array=1-10

# TODO replace with local paths
source "</path/to/nipoppy_env>"

SUBJECT_LIST="</path/to/subject_list>"
SESSION_ID="01"
GLOBAL_CONFIG="/path/to/global_configs.json"

echo "Number subjects found: `cat $SUBJECT_LIST | wc -l`"

SUBJECT_ID=`sed -n "${SGE_TASK_ID}p" $SUBJECT_LIST`
echo "Subject ID: $SUBJECT_ID"
	
python "<>/run_fmriprep.py" \
--global_config $GLOBAL_CONFIG \
--participant_id sub-$SUBJECT_ID \
--session_id $SESSION_ID \
--use_bids_filter
