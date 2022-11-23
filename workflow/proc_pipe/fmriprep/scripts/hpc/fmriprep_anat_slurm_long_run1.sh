#!/bin/bash

#SBATCH -J adni_long_ohbm_batch_bl
#SBATCH --time=23:00:00
#SBATCH --account=def-jbpoline
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=8G
# Outputs ----------------------------------
#SBATCH -o ./slurm_logs/%x-%A-%a_%j.out
#SBATCH -e ./slurm_logs/%x-%A-%a_%j.err
#SBATCH --mail-user=nikhil.bhagwat@mcgill.ca
#SBATCH --mail-type=ALL
# ------------------------------------------

#SBATCH --array=1-125

BIDS_DIR="/home/nikhil/scratch/adni_processing/bids/ohbm/baseline/"
SUBJECT_LIST="/home/nikhil/scratch/my_repos/brain-diff/metadata/adni_long_ohbm_subject_ids_tail125.txt"
WD_DIR="/home/nikhil/scratch/adni_processing/fmriprep/ohbm/baseline/"

echo "Starting task $SLURM_ARRAY_TASK_ID"
SUB_ID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" $SUBJECT_LIST)
echo "Subject ID: ${SUB_ID}"

module load singularity/3.8
../fmriprep_anat_sub_regular_20.2.7.sh ${BIDS_DIR} ${WD_DIR} ${SUB_ID}
