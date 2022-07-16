#!/bin/bash
DATA_NAME=(${@:1:1})
echo ${DATA_NAME}
hpc_system=(${@:2:1})
echo ${hpc_system}
COV_MODE=(${@:3:1})
echo ${COV_MODE}

if [ ${hpc_system} == 'sge' ]; then
# working dir for BIC server sge
WD_DIR="/data/pd/ppmi/scratch"
CODE_DIR="/data/pd/ppmi/scratch/mr_proc/workflow/HeuDiConv"
else
# working dir for CC
WD_DIR=${HOME}/scratch 
CODE_DIR=${WD_DIR}/mr_proc/HeuDiConv
fi 

# basic env and software
HEUDICONV_VERSION=0.9.0
SUB_LIST=${CODE_DIR}/${DATA_NAME}_subjects.list

#data dirs

#logging
LOG_DIR=${WD_DIR}/logs/heudiconv
LOG_FILE_r2=${DATA_NAME}_heudiconv_run2.log

#Select the proper heuristic file
if [ ${DATA_NAME} == 'PPMI' ]; then
    if [ ${COV_MODE} == 'T1' ]; then
        HEURISTIC_FILE="Heuristics_PPMI_T1.py"
    else
        HEURISTIC_FILE="Heuristics_PPMI_all.py"
    fi
elif [ ${DATA_NAME} == 'ADNI' ]; then
    if [ ${COV_MODE} == 'T1' ]; then
        HEURISTIC_FILE="Heuristics_ADNI_T1.py"
    else
        HEURISTIC_FILE="Heuristics_ADNI_all.py"
    fi
else
    if [ ${COV_MODE} == 'T1' ]; then
        HEURISTIC_FILE="Heuristics_PPMI_T1.py"
    else
        HEURISTIC_FILE="Heuristics_PPMI_all.py"
    fi
fi

# Get total number of subjects
N_SUB=$(cat ${SUB_LIST}|wc -l )

# submit subject conversion batch job
if [ ${hpc_system} == 'sge' ]; then
    # Clear previous logs
    rm -rf ${LOG_DIR}/vincentq_heudiconv_r2_*
    # running conversion
    CODE_FILE=${CODE_DIR}/heudiconv_run2.sge
    #N_SUB=1 # for single subject test purpose
    qsub -t 1-${N_SUB} -q origami.q ${CODE_FILE} ${DATA_NAME} ${HEURISTIC_FILE} ${HEUDICONV_VERSION} ${SUB_LIST} ${WD_DIR} >> ${LOG_FILE_r2}
    echo "SGE job submitted!"
else
# SLURM convention logs
RUN_ID=$(tail -c 9 ${DATA_NAME}_heudiconv_run2.log)
if [ -z $RUN_ID ];then
  echo 'no previous run found...'
else
  echo "previous run $RUN_ID found, deleting logs..."
  rm heudic_r2_vin-${RUN_ID}*.out
  rm heudic_r2_vin-${RUN_ID}*.err
fi
    # running conversion
    CODE_FILE=${CODE_DIR}/heudiconv_run2.slurm
    #N_SUB=1 # for single subject test purpose
    sbatch --array=1-${N_SUB} ${CODE_FILE} ${DATA_NAME} ${HEURISTIC_FILE} ${HEUDICONV_VERSION} ${SUB_LIST} ${WD_DIR} >> ${LOG_FILE_r2}
    echo "SLURM job submitted!"
fi 