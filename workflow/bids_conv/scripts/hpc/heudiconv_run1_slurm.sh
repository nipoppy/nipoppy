#!/bin/bash
#SBATCH --job-name=heudi_nikhil_r1
#SBATCH --time=3:00:00
#SBATCH --account=rrg_jbpoline
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4GB
# Outputs ----------------------------------
#SBATCH -o %x-%A-%a_%j.out
#SBATCH -e %x-%A-%a_%j.err
#SBATCH --mail-user=nikhil153@gmail.com
#SBATCH --mail-type=ALL

DATA_NAME=(${@:1:1})
echo ${DATA_NAME}

## SBATCH --array=1-117
# PPMI N=117
# ADNI N=???
# MNI-ET N = 42
# MNI-PD N = 56
# MNI-NC N = 36

WD_NAME="scratch"
#HEURISTIC_FILE="src/Heuristics_Abbas_all_T1_T2_fMRI_DTI_SWI.py"
WD_DIR="/scratch/nikhil/PD/qpn/"
DATA_DIR=${WD_DIR}/${DATA_NAME}
CODE_DIR="/home/nikhil/scratch/my_repos/ET_biomarker"
CON_IMG_DIR="/home/nikhil/scratch/my_containers"
SUB_LIST=${WD_DIR}/${DATA_NAME}_subjects.list
BIDS_DIR=${DATA_DIR}_BIDS
INFO_DIR=${DATA_DIR}_INFO
INFO_SUM_DIR=${DATA_DIR}_INFO_SUM

# singularity folders
SINGULARITY_MNT_DIR=/${WD_NAME}
SINGULARITY_OUT_DIR=${SINGULARITY_MNT_DIR}/${DATA_NAME}_BIDS
# run heudiconv at subject level.
echo "Starting task ${SLURM_ARRAY_TASK_ID}"
DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" ${SUB_LIST} )
echo "Current Directory: " ${WD_DIR}
DIR_STR=${DIR//\//" " }
echo ${DIR_STR}

subject_id=${DIR_STR}
echo ${DATA_NAME} ${subject_id}

singularity run -B ${WD_DIR}:${SINGULARITY_MNT_DIR} \
${CON_IMG_DIR}/heudiconv_v0.8.0.simg \
-d ${SINGULARITY_MNT_DIR}/${DATA_NAME}/*/* \
-s ${subject_id} -c none \
-f convertall \
-o ${SINGULARITY_OUT_DIR} \
--overwrite
#-ss ${ses_id} \
#--grouping studyUID \

echo "Step3: Heudiconv Run1 finishted!"
