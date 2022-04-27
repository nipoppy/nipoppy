#!/bin/bash
DATA_NAME=(${@:1:1})
echo ${DATA_NAME}

WD_DIR=${HOME}/scratch
DATA_DIR=${WD_DIR}/${DATA_NAME}
BIDS_DIR=${DATA_DIR}_BIDS
CODE_DIR=${WD_DIR}/ET_biomarker/scripts/fmriprep

CODE_SLURM=${CODE_DIR}/fmriprep_anat_sub.slurm
CODE_COLLECT=${CODE_DIR}/fmriprep_anat_sub.format

CON_IMG=${WD_DIR}/container_images/fmriprep_v20.2.0.simg
#DERIVS_DIR=${DATA_DIR}_fmriprep_anat_20.2.0
LOG_DIR=${DATA_DIR}_fmriprep_anat.log

chmod +x ${CODE_SLURM}
chmod +x ${CODE_COLLECT}

echo "Step1: subjects folder created!"
echo "Step2: starting fmriprep-SP!"
#echo "Submitting sub-3274, sub-3523, sub-3765, sub-3900!"

# PPMI
# err 22688556
#SUB_ID=3274
#sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG} ${SUB_ID} >> ${LOG_DIR}
# err 22686840
#SUB_ID=3523
#sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG} ${SUB_ID} >> ${LOG_DIR}
# err 22688314
#SUB_ID=3765
#sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG} ${SUB_ID} >> ${LOG_DIR}

# ADNI
# err 22953764_95
#SUB_ID=021S0984
#sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG} ${SUB_ID} >> ${LOG_DIR}
# err 22953764_120
SUB_ID=037S4028
sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG} ${SUB_ID} >> ${LOG_DIR}
# err 22953764_121
#SUB_ID=098S4018
#sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG} ${SUB_ID} >> ${LOG_DIR}
# err 22953764_126
#SUB_ID=128S4607
#sbatch ${CODE_SLURM} ${DATA_NAME} ${CON_IMG} ${SUB_ID} >> ${LOG_DIR}
echo "Submission finished!"
