#!/bin/bash
#SBATCH --job-name=heudi_vinc_r1
#SBATCH --time=3:00:00
#SBATCH --account=def-jbpoline
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4GB
# Outputs ----------------------------------
#SBATCH -o %x-%A-%a_%j.out
#SBATCH -e %x-%A-%a_%j.err
#SBATCH --mail-user=vincent.w.qing@gmail.com
#SBATCH --mail-type=ALL

DATA_NAME=(${@:1:1})
CON_IMG=(${@:2:1})

echo converting ${DATA_NAME} using ${CON_IMG}

WD_NAME="scratch"
WD_DIR=${HOME}/${WD_NAME}
DATA_DIR=${WD_DIR}/${DATA_NAME}
SUB_LIST=${WD_DIR}/${DATA_NAME}_subjects.list
BIDS_DIR=${DATA_DIR}_BIDS

# singularity folders
SINGULARITY_MNT_DIR=/${WD_NAME}
SINGULARITY_OUT_DIR=${SINGULARITY_MNT_DIR}/${DATA_NAME}_BIDS
# run heudiconv at subject level.
echo "Starting task ${SLURM_ARRAY_TASK_ID}"
DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" ${SUB_LIST} )
echo "Current Directory: " ${WD_DIR}
DIR_STR=${DIR//\//" " }
echo ${DIR_STR}
#Get subject ID
if [ ${DATA_NAME} == 'PPMI' ]; then
    DATA_DIR_LEN_OFFSET=32
elif [ ${DATA_NAME} == 'ADNI' ]; then
    DATA_DIR_LEN_OFFSET=32
else
    DATA_DIR_LEN_OFFSET=29
fi
subject_id=${DIR_STR[@]:DATA_DIR_LEN_OFFSET}
echo ${DATA_NAME} ${subject_id}
# create different folder patterns for different datasets
if [ ${DATA_NAME} == 'PPMI' ]; then
singularity run -B ${WD_DIR}:${SINGULARITY_MNT_DIR} \
${CON_IMG} \
-d ${SINGULARITY_MNT_DIR}/${DATA_NAME}/{subject}/*/*/*/*.dcm \
-s ${subject_id} -c none \
-f convertall \
-o ${SINGULARITY_OUT_DIR} \
--overwrite
else
singularity run -B ${WD_DIR}:${SINGULARITY_MNT_DIR} \
${CON_IMG} \
-d ${SINGULARITY_MNT_DIR}/${DATA_NAME}/{subject}/*/*/*/*.dcm \
-s ${subject_id} -c none \
-f convertall \
-o ${SINGULARITY_OUT_DIR} \
--overwrite
#-ss ${ses_id} \
#--grouping studyUID \
fi
echo "Step3: Heudiconv Run1 finishted!"
