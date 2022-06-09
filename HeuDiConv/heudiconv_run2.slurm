#!/bin/bash
#SBATCH --job-name=heudic_r2_vin
#SBATCH --time=6:00:00
#SBATCH --account=def-jbpoline
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

echo "Converting: " ${DATA_NAME} " subjects: " ${SUB_LIST}  " with heuristics: " ${HEURISTIC_FILE} " and contatiner: " ${CON_IMG}

# prepare folders
WD_DIR=${HOME}/"scratch"
DATA_DIR=${WD_DIR}/${DATA_NAME}
BIDS_DIR=${WD_DIR}/${DATA_NAME}_BIDS
CODES_DIR=${WD_DIR}/mr_proc/HeuDiConv
TMP_DIR=${DATA_DIR}_convTMP

# singularity folders
SINGULARITY_MNT_DIR=/scratch
SINGULARITY_OUT_DIR=${SINGULARITY_MNT_DIR}/${DATA_NAME}_BIDS
SINGULARITY_CODES_DIR=/codes
SINGULARITY_HEURISTICS=${SINGULARITY_MNT_DIR}/mr_proc/HeuDiConv/${HEURISTIC_FILE}

# run heudiconv at subject level.
echo "Starting task ${SLURM_ARRAY_TASK_ID}"
DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" ${SUB_LIST})
# DIR=$(sed -n "3p" ${SUB_LIST}) # this line for test subject

DIR_STR=${DIR//\//" " }
#Get subject ID
if [ ${DATA_NAME} == 'PPMI' ];then
    DATA_DIR_LEN_OFFSET=32
    subject_id=${DIR_STR[@]:DATA_DIR_LEN_OFFSET}
    echo ${subject_id}
    seq_list=$(ls -1 $DIR)
    ses_list=()
    sub_tmp_dir=${TMP_DIR}/${subject_id}
# create tmp subject dir
    if [ -d ${sub_tmp_dir} ];then
        rm -rf ${sub_tmp_dir}/*
        echo ${subject_id} " cleared!"
    else
        mkdir -p ${sub_tmp_dir}
    echo ${subject_id} " tmp dir created..."
    fi
# reorganize PPMI subject forder indexed by sessions
    for seq in $(ls -1 $DIR);
    do
        for date in $(ls -1 $DIR/"$seq");
        do
        ses_tmp=$(echo ${date:0:10} | tr -d  '-')
        ses_dir_tmp=${sub_tmp_dir}/${ses_tmp}
        if [ -d ${ses_dir_tmp} ];then
            rsync -a ${DIR}/${seq}/${date}/* ${ses_dir_tmp}
        else
            ses_list+=("${ses_tmp}")
            mkdir -p ${ses_dir_tmp}
        fi
        done
    done
    echo ${ses_list[@]}
    for ses_i in ${ses_list[@]};
    do
# conversion
    echo "converting session: " ${ses_i}
    singularity run --cleanenv \
    -B ${WD_DIR}:${SINGULARITY_MNT_DIR} ${CON_IMG} \
    -d ${SINGULARITY_MNT_DIR}/${DATA_NAME}_convTMP/{subject}/{session}/*/*.dcm \
    -s ${subject_id} \
    -f ${SINGULARITY_HEURISTICS} \
    -ss "${ses_i}" \
    --grouping studyUID \
    -c dcm2niix -b --overwrite --minmeta \
    -o ${SINGULARITY_OUT_DIR}
    done
# clear tmp subject dir
    rm -rf ${sub_tmp_dir}

elif [ ${DATA_NAME} == 'ADNI' ]; then
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
    echo ${DATA_NAME} "-" ${subject_id} "-" ${SES}
fi

echo "Step5: Heudiconv Run2 finishted, conversion complete!"
