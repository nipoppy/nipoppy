#!/bin/bash
DATA_NAME=(${@:1:1})
echo ${DATA_NAME}

WD_DIR=${HOME}/scratch
DATA_DIR=${WD_DIR}/${DATA_NAME}
BIDS_DIR=${DATA_DIR}_BIDS
CODE_DIR=${WD_DIR}/src
CODE_SLURM=${CODE_DIR}/fmriprep_anat.slurm
CODE_COLLECT=${CODE_DIR}/fmriprep_anat.format

SUB_LIST=${CODE_DIR}/${DATA_NAME}_fmriprep_preopt.list
CON_IMG_DIR=${WD_DIR}/container_images/fmriprep_v20.1.1.simg

OUT_DIR=${DATA_DIR}_fmriprep_anat_20.1.1
LOG_DIR=${DATA_DIR}_fmriprep_anat.log
SLURM_LOG_DIR=${DATA_DIR}_fmriprep_anat_slurm_log
WORK_DIR=${DATA_DIR}_fmriprep_anat_work

FREESURFER_LICENSE="${WD_DIR}/container_images"
TEMPLATEFLOW_HOST_HOME=$HOME/scratch/templateflow

RUN_ID=$(tail -c 9 ${LOG_DIR})
if [ -z $RUN_ID ];then
  echo 'no previous run found...'
else
  echo "previous run $RUN_ID found, deleting logs..."
  rm fmriprep_vince-${RUN_ID}*.out
  rm fmriprep_vince-${RUN_ID}*.err
fi

rm -rf ${OUT_DIR}
rm -rf ${OUT_DIR}.tar.gz
rm -rf ${OUT_DIR}_freesurfer.tar.gz
rm -rf ${WORK_DIR}
rm -rf ${SLURM_LOG_DIRDIR}
rm -rf ${SLURM_LOG_DIR}.tar.gz
rm -rf ${SUB_LIST}

chmod +x ${CODE_SLURM}
chmod +x ${CODE_COLLECT}

awk -F"\t" '{print $1}' ${BIDS_DIR}/participants.tsv >> ${SUB_LIST}
sed -i '1d' ${SUB_LIST}

echo "Step1: subjects list created!"

if [ -d ${OUT_DIR} ];then
  echo "fmriprep out dir already exists!"
else
  mkdir -p ${OUT_DIR}
fi

if [ -d ${WORK_DIR} ];then
  echo "fmriprep work dir already exists!"
else
  mkdir -p ${WORK_DIR}
fi

if [ -d ${SLURM_LOG_DIR} ];then
  echo "fmriprep slurm log dir already exists!"
else
  mkdir -p ${SLURM_LOG_DIR}
fi

if [ -d ${TEMPLATEFLOW_HOST_HOME} ];then
	echo "Templateflow dir already exists!"
else
	mkdir -p ${TEMPLATEFLOW_HOST_HOME}
	python -c "from templateflow import api; api.get('MNI152NLin2009cAsym')"
	python -c "from templateflow import api; api.get('OASIS30ANTs')"
fi

echo "Step2: starting fmriprep!"
sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG_DIR} >> ${LOG_DIR}
