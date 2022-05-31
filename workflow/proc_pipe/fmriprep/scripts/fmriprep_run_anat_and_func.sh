#!/bin/bash

# Author: nikhil153
# Last update: 16 Feb 2022

if [ "$#" -ne 3 ]; then
  echo "Please provide paths to the bids_dir, working_dir and subject ID (i.e. subdir inside BIDS_DIR)"
  exit 1
fi

BIDS_DIR=$1
WD_DIR=$2
SUB_ID=$3

#BIDS_DIR="/scratch/nikhil/ukbb_processing/fmriprep/BIDS_DIR"
BIDS_FILTER="bids_filter.json" # to ignore NM T1 files. This needs to be in BIDS_DIR. 

CON_IMG="/data/pd/qpn/containers/fmriprep_20.2.7.sif"
#CON_IMG="/home/nikhil/projects/my_containers/fmriprep_20.2.7.sif"
SINGULARITY_PATH="/opt/bin/singularity"

# CHECK IF YOU HAVE TEMPLATEFLOW
# TEMPLATEFLOW_HOST_HOME="/home/nikhil/scratch/templateflow"
TEMPLATEFLOW_HOST_HOME="/data/pd/qpn/templateflow" #"/home/nikhil/projects/templateflow"

DERIVS_DIR=${WD_DIR}/output

LOG_FILE=${WD_DIR}_fmriprep_anat.log
echo "Starting fmriprep proc with container: ${CON_IMG}"
echo ""
echo "Using working dir: ${WD_DIR} and subject ID: ${SUB_ID}"

# Create subject specific dirs
FMRIPREP_HOME=${DERIVS_DIR}/fmriprep_home_${SUB_ID}
echo "Processing: ${SUB_ID} with home dir: ${FMRIPREP_HOME}"
mkdir -p ${FMRIPREP_HOME}

LOCAL_FREESURFER_DIR="${DERIVS_DIR}/freesurfer-6.0.1"
mkdir -p ${LOCAL_FREESURFER_DIR}

# Prepare some writeable bind-mount points.
FMRIPREP_HOST_CACHE=$FMRIPREP_HOME/.cache/fmriprep
mkdir -p ${FMRIPREP_HOST_CACHE}

# Make sure FS_LICENSE is defined in the container.
mkdir -p $FMRIPREP_HOME/.freesurfer
export SINGULARITYENV_FS_LICENSE=$FMRIPREP_HOME/.freesurfer/license.txt
cp ${WD_DIR}/license.txt ${SINGULARITYENV_FS_LICENSE}

# Designate a templateflow bind-mount point
export SINGULARITYENV_TEMPLATEFLOW_HOME="/templateflow"

# Singularity CMD 
SINGULARITY_CMD="$SINGULARITY_PATH run \
-B ${BIDS_DIR}:/data_dir \
-B ${FMRIPREP_HOME}:/home/fmriprep --home /home/fmriprep --cleanenv \
-B ${DERIVS_DIR}:/output \
-B ${TEMPLATEFLOW_HOST_HOME}:${SINGULARITYENV_TEMPLATEFLOW_HOME} \
-B ${WD_DIR}:/work \
-B ${LOCAL_FREESURFER_DIR}:/fsdir \
 ${CON_IMG}"

# Remove IsRunning files from FreeSurfer
find ${LOCAL_FREESURFER_DIR}/sub-$SUB_ID/ -name "*IsRunning*" -type f -delete

# Compose the command line
cmd="${SINGULARITY_CMD} /data_dir /output participant --participant-label $SUB_ID \
-w /work --output-spaces MNI152NLin2009cAsym:res-2 anat fsnative fsaverage5 \
--fs-subjects-dir /fsdir \
--skip_bids_validation \
--bids-database-dir /work/first_run/bids_db/
--fs-license-file /home/fmriprep/.freesurfer/license.txt \
--return-all-components -v \
--write-graph  --notrack \
--bids-filter-file /data_dir/${BIDS_FILTER}"

#--bids-filter-file ${BIDS_FILTER} 
# --anat-only --cifti-out 91k"
#--bids-database-dir /work/first_run: creating this during first test run. If successful, all other subjects will use this and avoid reindexing same bids_db \

# Setup done, run the command
#echo Running task ${SLURM_ARRAY_TASK_ID}
unset PYTHONPATH
echo Commandline: $cmd
eval $cmd
exitcode=$?

# Output results to a table
echo "$SUB_ID    ${SLURM_ARRAY_TASK_ID}    $exitcode"
echo Finished tasks ${SLURM_ARRAY_TASK_ID} with exit code $exitcode
rm -rf ${FMRIPREP_HOME}
exit $exitcode

echo "Submission finished!"
