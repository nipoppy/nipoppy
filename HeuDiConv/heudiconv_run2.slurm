#!/bin/bash
#SBATCH --job-name=heudic_r2_vin
#SBATCH --time=6:00:00
#SBATCH --account=rrg-jbpoline
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=4GB
# Outputs ----------------------------------
#SBATCH -o %x-%A-%a_%j.out
#SBATCH -e %x-%A-%a_%j.err
#SBATCH --mail-user=vincent.w.qing@gmail.com
#SBATCH --mail-type=ALL
# usage:
#sbatch heudiconv_slurm_run2.sh ${WD_NAME} ${STUDY_NAME} ${SEARCH_LV} ${HEURISTIC_FILE} >> ${LOG_FILE}_run2.log
DATA_NAME=(${@:1:1})
HEURISTIC_FILE=(${@:2:1})
CON_IMG=(${@:3:1})
SUB_LIST=(${@:4:1})

echo "Converting: " ${DATA_NAME} " subjects: " ${SUB_LIST}  " with heuristics: " ${HEURISTIC_FILE} " contatiner: " ${CON_IMG}

WD_DIR=${HOME}/"scratch"
BIDS_DIR=${WD_DIR}/${DATA_NAME}_BIDS
# singularity folders
SINGULARITY_MNT_DIR=/scratch
SINGULARITY_OUT_DIR=${SINGULARITY_MNT_DIR}/${DATA_NAME}_BIDS
CODES_DIR=${WD_DIR}/ET_biomarker/scripts/heudiconv
SINGULARITY_CODES_DIR=/codes
# run heudiconv at session level.
echo "Starting task ${SLURM_ARRAY_TASK_ID}"
DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" ${SUB_LIST})
echo "Current Directory: " ${DIR}
DIR_STR=${DIR//\//" " }
#Get subject ID
if [ ${DATA_NAME} = 'PPMI' ]; then
    DATA_DIR_LEN_OFFSET=32
    subject_id=${DIR_STR[@]:DATA_DIR_LEN_OFFSET}
    echo ${DATA_NAME} * ${subject_id} 
    singularity run --cleanenv -B ${WD_DIR}:${SINGULARITY_MNT_DIR} ${CON_IMG} \
    -d ${SINGULARITY_MNT_DIR}/${DATA_NAME}/{subject}/*/*/{session}/*.dcm \
    -s ${subject_id} \
    -ss ${SES}\
    -f ${SINGULARITY_MNT_DIR}/mr_proc/HeuDiConv/${HEURISTIC_FILE} \
    --grouping studyUID \
    -c dcm2niix -b --overwrite --minmeta \
    -o ${SINGULARITY_OUT_DIR}

elif [ ${DATA_NAME} = 'ADNI' ]; then
    DATA_DIR_LEN_OFFSET=32
    subject_id=${DIR_STR[@]:DATA_DIR_LEN_OFFSET}
    SES=$(cat ${DATA_NAME}_sessions/${subject_id})
    echo ${DATA_NAME} * ${subject_id} * ${SES}
    singularity run --cleanenv -B ${WD_DIR}:${SINGULARITY_MNT_DIR} ${CON_IMG} \
    -d ${SINGULARITY_MNT_DIR}/${DATA_NAME}/{subject}/*/*/{session}/*.dcm \
    -s ${subject_id} \
    -ss ${SES}\
    -f ${SINGULARITY_MNT_DIR}/mr_proc/HeuDiConv/${HEURISTIC_FILE} \
    --grouping studyUID \
    -c dcm2niix -b --overwrite --minmeta \
    -o ${SINGULARITY_OUT_DIR}
else
    DATA_DIR_LEN_OFFSET=29
    subject_id=${DIR_STR[@]:DATA_DIR_LEN_OFFSET}
    echo ${DATA_NAME} * ${subject_id} * ${SES}
fi

echo "Step5: Heudiconv Run2 finishted, conversion complete!"
