#!/bin/bash
if [ "$#" -ne 3 ]; then
DATA_NAME=(${@:1:1})
CLEAN_RUN_FLAG=(${@:2:1})
RUN_LIST_FLAG='Y'
echo "Cleaning old results: "${CHECK_DIR}
else
DATA_NAME=(${@:1:1})
SUB_ID=(${@:2:1})
SES_ID=(${@:3:1})
RUN_LIST_FLAG='N'
echo 'Rerunning subj: ' ${SUB_ID} ', ses' ${SES_ID}
fi
echo ${DATA_NAME}

WD_DIR=${HOME}/scratch
DATA_DIR=${WD_DIR}/${DATA_NAME}
BIDS_DIR=${DATA_DIR}_BIDS

CODE_DIR=${WD_DIR}/interventionMDD/preproc
CODE_SLURM=${CODE_DIR}/fmriprep_anat_sub.slurm
CODE_COLLECT=${CODE_DIR}/fmriprep_anat.format
TEMPLATEFLOW_HOST_HOME=${WD_DIR}/templateflow
RUN_LIST=${CODE_DIR}/runningMDD_rerun.csv

FMRIPREP_VER=20.2.7
LOG_FILE=${WD_DIR}/${DATA_NAME}_fmriprep_anat.log

# +x for codes and remove previous logs
chmod +x ${CODE_SLURM}
chmod +x ${CODE_COLLECT}
rm fmriprep_subj_vince*
# check templateflow
if [ -d ${TEMPLATEFLOW_HOST_HOME} ];then
	echo "Templateflow dir already exists!"
else
	mkdir -p ${TEMPLATEFLOW_HOST_HOME}
	python -c "from templateflow import api; api.get('MNI152NLin2009cAsym')"
	python -c "from templateflow import api; api.get('OASIS30ANTs')"
fi

# creating folders and envs
if [ ${CLEAN_RUN_FLAG} == 'Y' ];then
# create session outputs
#RUN_LIST="preproc/runningMDD_rerun.csv" # for easy test
for SES_ in $(sed -n '/sub/s/^.*,\([0-9]*\).*$/\1/p' ${RUN_LIST} | sort -u)
do
echo "creating folders for session "$SES_
OUT_DIR=${DATA_DIR}_ses-${SES_}_fmriprep_anat_${FMRIPREP_VER}
if [ -d ${OUT_DIR} ];then
rm -rf ${OUT_DIR}
fi
mkdir -p ${OUT_DIR}
done
LOG_DIR=${DATA_DIR}_fmriprep_anat_log
if [ -d ${LOG_DIR} ];then
  rm -rf ${LOG_DIR}
fi
mkdir -p ${LOG_DIR}
fi

if [ ${RUN_LIST_FLAG} == 'Y' ];then
#RUN_LIST="runningMDD_rerun.csv" # for easy test
while read line; do
    # Do what you want to $name
    SUB_ID_STR="$(cut -d',' -f1 <<<${line})"
    SUB_ID="$(cut -d'-' -f2 <<<${SUB_ID_STR})"
    SES_ID="$(cut -d',' -f2 <<<${line})"
    echo 'rerunning subj: ' ${SUB_ID} ', ses' ${SES_ID}
    sbatch ${CODE_SLURM} ${DATA_NAME} ${FMRIPREP_VER} ${SUB_ID} ${SES_ID} >> ${LOG_FILE}
done < ${RUN_LIST}

else
sbatch ${CODE_SLURM} ${DATA_NAME} ${FMRIPREP_VER} ${SUB_ID} ${SES_ID} >> ${LOG_FILE}
fi
echo "fmriprep job submitted!"
