#!/bin/bash
DATA_NAME=(${@:1:1})
echo ${DATA_NAME}
COV_MODE=(${@:2:1})
echo ${COV_MODE}

WD_NAME="scratch"
LOG_FILE=${DATA_NAME}_heudiconv_run2.log
WD_DIR=${HOME}/${WD_NAME}
DATA_DIR=${WD_DIR}/${DATA_NAME}
CODE_DIR=${WD_DIR}/ET_biomarker/scripts/heudiconv/heudiconv_run2.slurm
SUB_LIST=${DATA_DIR}_subjects.list
CON_IMG=${WD_DIR}/container_images/heudiconv_v0.8.0.simg
N_SUB=$(cat ${SUB_LIST}|wc -l )
#Select the proper heuristic file
if [ ${DATA_NAME} = 'PPMI' ]; then
    if [ ${COV_MODE} = 'T1' ]; then
        HEURISTIC_FILE="Heuristics_PPMI_T1.py"
    else
        HEURISTIC_FILE="Heuristics_PPMI_all.py"
    fi
elif [ ${DATA_NAME} = 'ADNI' ]; then
    if [ ${COV_MODE} = 'T1' ]; then
        HEURISTIC_FILE="Heuristics_ADNI_T1.py"
    else
        HEURISTIC_FILE="Heuristics_ADNI_all.py"
    fi
else
    if [ ${COV_MODE} = 'T1' ]; then
        HEURISTIC_FILE="Heuristics_MNI-ET_T1.py"
    else
        HEURISTIC_FILE="Heuristics_MNI-ET_all.py"
    fi
fi

RUN_ID=$(tail -c 9 ${DATA_NAME}_heudiconv_run2.log)
if [ -z $RUN_ID ];then
  echo 'no previous run found...'
else
  echo "previous run $RUN_ID found, deleting logs..."
  rm heudic_r2_vin-${RUN_ID}*.out
  rm heudic_r2_vin-${RUN_ID}*.err
fi

# submit batch job
sbatch --array=1-${N_SUB} ${CODE_DIR} ${DATA_NAME} ${HEURISTIC_FILE} ${CON_IMG} ${SUB_LIST}>> ${LOG_FILE}
