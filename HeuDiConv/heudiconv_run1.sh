#!/bin/bash
DATA_NAME=(${@:1:1})
echo ${DATA_NAME}
hpc_system=(${@:2:1})
echo ${hpc_system}
CHECK_DIR=(${@:3:1})
echo ${CHECK_DIR}

if [ ${hpc_system} == 'sge' ]; then
# working dir for BIC server sge
WD_DIR="/data/pd/ppmi/scratch"
CODE_DIR="/data/pd/ppmi/mr_proc/HeuDiConv"
else
# working dir for CC
WD_DIR=${HOME}/scratch 
CODE_DIR=${WD_DIR}/mr_proc/HeuDiConv
fi 

# basic env and software
HEUDICONV_VERSION=0.9.0
SEARCH_LV=1
SUB_LIST=${CODE_DIR}/${DATA_NAME}_subjects.list

#data
DATA_DIR=${WD_DIR}/${DATA_NAME}
ORGANIZED_DATA_NAME=${DATA_NAME}_SessionOrganized
BIDS_DIR=${DATA_DIR}_BIDS
INFO_DIR=${DATA_DIR}_INFO

#logging
LOG_DIR=${WD_DIR}/logs/heudiconv
LOG_FILE_prefix=${DATA_NAME}_heudiconv
LOG_FILE_r1=${LOG_FILE_prefix}_run1.log
LOG_FILE_r2=${LOG_FILE_prefix}_run2.log

# load modules on HPC
#module load singularity

RUN_ID=$(tail -c 9 ${LOG_FILE_r1})
if [ -z $RUN_ID ];then
  echo 'no previous run found...'
else
  echo "previous run $RUN_ID found, deleting logs..."
  rm -rf ${LOG_DIR}/vincentq_heudiconv_r1_*
fi

chmod +x ${CODE_DIR}/heudiconv_run2.sh
chmod +x ${CODE_DIR}/heudiconv_run1.format
chmod +x ${CODE_DIR}/heudiconv_run2.format

# get all subject dicom foldernames.
rm ${SUB_LIST}
find ${ORGANIZED_DATA_NAME} -maxdepth ${SEARCH_LV} -mindepth ${SEARCH_LV} >> ${SUB_LIST}
N_SUB=$(cat ${SUB_LIST}|wc -l )
echo "Step1: subjects.list created!"

# folder check
if [ ${CHECK_DIR} == 'Y' ];then
if [ -d ${BIDS_DIR} ];then
  rm -rf ${BIDS_DIR}
  rm -rf res/${BIDS_DIR}.zip
  mkdir -p ${BIDS_DIR}
  echo "BIDS folder already exists, cleared!"
else
  mkdir -p ${BIDS_DIR}
fi
if [ -d ${INFO_DIR} ];then
  rm -rf ${INFO_DIR}
  rm -rf res/${INFO_DIR}.zip 
  mkdir -p ${INFO_DIR}
  echo "INFO_SUM folder already exists, cleared!"
else
  mkdir -p ${INFO_DIR}
fi
if [ -d ${LOG_DIR} ];then
  rm -rf ${LOG_DIR}/*
  rm -rf res/${LOG_DIR}.zip
  echo "SLURM_LOG_OUT_DIR_run1 folder already exists, cleared!"
else
  mkdir -p ${LOG_DIR}
fi
else
echo "Step2: folders check skipped!"
fi

# submit batch job
if [ ${hpc_system} == 'sge' ]; then
    chmod +x ${CODE_DIR}/heudiconv_run1.sge
    chmod +x ${CODE_DIR}/heudiconv_run2.sge
    CODE_FILE=${CODE_DIR}/heudiconv_run1.sge
    #N_SUB=1 # for single subject test purpose
    qsub -t 1-${N_SUB} -q origami.q ${CODE_FILE} ${DATA_NAME} ${HEUDICONV_VERSION} ${SUB_LIST} ${WD_DIR} >> ${LOG_FILE_r1}
    echo "SGE job submitted!"
else
    chmod +x ${CODE_DIR}/heudiconv_run1.slurm
    chmod +x ${CODE_DIR}/heudiconv_run2.slurm
    CODE_FILE=${CODE_DIR}/heudiconv_run1.slurm
    #N_SUB=1 # for single subject test purpose
    sbatch --array=1-${N_SUB} ${CODE_FILE} ${DATA_NAME} ${HEUDICONV_VERSION} ${SUB_LIST} ${WD_DIR} >> ${LOG_FILE_r1}
    echo "SLURM job submitted!"
fi 
