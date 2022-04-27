#!/bin/bash
#
#SBATCH -J fmriprep_subj_vince
#SBATCH --time=48:00:00
#SBATCH --account=def-jbpoline
#SBATCH --cpus-per-task=12
#SBATCH --mem-per-cpu=4G
# Outputs ----------------------------------
#SBATCH -o %x-%A-%a_%j.out
#SBATCH -e %x-%A-%a_%j.err
# ------------------------------------------

DATA_NAME=(${@:1:1})
FMRIPREP_VER=(${@:2:1})
SUB_ID=(${@:3:1})
SES_ID=(${@:4:1})

WD_DIR=${HOME}/scratch
DATA_DIR=${WD_DIR}/${DATA_NAME}
BIDS_DIR=${DATA_DIR}_BIDS
CON_IMG=${WD_DIR}/container_images/fmriprep_${FMRIPREP_VER}.sif
DERIVS_DIR=${DATA_DIR}_ses-${SES_ID}_fmriprep_anat_${FMRIPREP_VER}

# Need to change according to projects
CODE_DIR=${WD_DIR}/interventionMDD/preproc
BIDS_FILTER="anat_ses-${SES_ID}.json"
echo ${SUB_ID}***${BIDS_FILTER}

FMRIPREP_HOME=fmriprep_home_${SUB_ID}_${SES_ID}
LOG_DIR=${DATA_DIR}_fmriprep_anat_slurm_log
WORK_DIR=${DATA_DIR}_work_${SUB_ID}_${SES_ID}
echo "Processing: sub-${SUB_ID}, session ${SES_ID} with home dir: ${FMRIPREP_HOME}"
mkdir -p ${FMRIPREP_HOME}
mkdir -p ${WORK_DIR}

LOCAL_FREESURFER_DIR="${DERIVS_DIR}/freesurfer-6.0.1"
mkdir -p ${LOCAL_FREESURFER_DIR}
# Prepare some writeable bind-mount points.
TEMPLATEFLOW_HOST_HOME=$HOME/scratch/templateflow
FMRIPREP_HOST_CACHE=$FMRIPREP_HOME/.cache/fmriprep
mkdir -p ${FMRIPREP_HOST_CACHE}

# Make sure FS_LICENSE is defined in the container.
mkdir -p $FMRIPREP_HOME/.freesurfer
export SINGULARITYENV_FS_LICENSE=$FMRIPREP_HOME/.freesurfer/license.txt
cp container_images/license.txt ${SINGULARITYENV_FS_LICENSE}

# Designate a templateflow bind-mount point
export SINGULARITYENV_TEMPLATEFLOW_HOME="/templateflow"
SINGULARITY_CMD="singularity run -B ${FMRIPREP_HOME}:/home/fmriprep --home /home/fmriprep --cleanenv \
-B ${BIDS_DIR}:/data:ro \
-B ${DERIVS_DIR}:/output \
-B ${CODE_DIR}:/codes \
-B ${TEMPLATEFLOW_HOST_HOME}:${SINGULARITYENV_TEMPLATEFLOW_HOME} \
-B ${WORK_DIR}:/work \
-B ${LOCAL_FREESURFER_DIR}:/fsdir ${CON_IMG}"

# Remove IsRunning files from FreeSurfer
find ${LOCAL_FREESURFER_DIR}/sub-$SUB_ID/ -name "*IsRunning*" -type f -delete

# Compose the command line
cmd="${SINGULARITY_CMD} /data /output participant --participant-label $SUB_ID \
-w /work --output-spaces MNI152NLin2009cAsym:res-2 anat fsnative fsaverage5 \
--fs-subjects-dir /fsdir \
--fs-license-file /home/fmriprep/.freesurfer/license.txt \
--cifti-out 91k --return-all-components --anat-only --ignore t2w --longitudinal \
--bids-filter-file /codes/${BIDS_FILTER} \
--write-graph --skip_bids_validation --notrack"
# --bids-filter-file ${BIDS_FILTER} --anat-only --cifti-out 91k 
# Setup done, run the command
#echo Running task ${SLURM_ARRAY_TASK_ID}
echo Commandline: $cmd
unset PYTHONPATH
eval $cmd
exitcode=$?

# Output results to a table
echo "$SUB_ID    ${SLURM_ARRAY_TASK_ID}    $exitcode" \
      >> ${LOG_DIR}/${SLURM_JOB_NAME}.tsv
echo Finished tasks ${SLURM_ARRAY_TASK_ID} with exit code $exitcode
rm -rf ${FMRIPREP_HOME}
rm -rf ${WORK_DIR}
exit $exitcode
