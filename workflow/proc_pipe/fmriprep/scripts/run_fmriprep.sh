#!/bin/bash

# Author: nikhil153
# Last update: 16 Feb 2022

if [ "$#" -ne 20 ]; then
  echo "Please provide DATA_DIR, FMRIPREP_DIR, FMRIPREP_IMG, FS_DIR, FS_LICENSE, PARTICIPANT_ID, \
        CONTAINER, TEMPLATEFLOW_DIR, SINGULAIRTY_RUN_CMD, \
        BIDS_FILTER flag (typically to filter out sessions), ANAT_ONLY flag"
  exit 1
fi

while getopts d:o:f:l:p:c:r:t:b:a: flag
do
    case "${flag}" in
        d) DATA_DIR=${OPTARG};;
        o) FMRIPREP_DIR=${OPTARG};;
        f) FS_DIR=${OPTARG};;
        l) FS_LICENSE=${OPTARG};;
        p) PARTICIPANT_ID=${OPTARG};;
        c) CONTAINER=${OPTARG};;
        r) RUN_CMD=${OPTARG};; 
        t) TEMPLATEFLOW_DIR=${OPTARG};;                 
        b) BIDS_FILTER=${OPTARG};;
        a) ANAT_ONLY=${OPTARG};;
    esac
done

# Container
SINGULARITY_CONTAINER=$CONTAINER
SINGULARITY_PATH=$RUN_CMD

# TEMPLATEFLOW
TEMPLATEFLOW_HOST_HOME=$TEMPLATEFLOW_DIR

# paths
BIDS_DIR=$DATA_DIR
FMRIPREP_DIR=$FMRIPREP_DIR
FS_DIR=$FS_DIR
# FS license.txt path
LOCAL_FS_LICENSE=$FS_LICENSE

FP_OUT_DIR=${FMRIPREP_DIR}/output

LOG_FILE=${FMRIPREP_DIR}_fmriprep.log
echo "Starting fmriprep proc with container: ${SINGULARITY_CONTAINER}"
echo ""
echo "Using working dir: ${FMRIPREP_DIR} and subject ID: ${PARTICIPANT_ID}"

# Create subject specific dirs
FMRIPREP_HOME=${FP_OUT_DIR}/fmriprep_home_${PARTICIPANT_ID}
echo "Processing: ${PARTICIPANT_ID} with home dir: ${FMRIPREP_HOME}"
mkdir -p ${FMRIPREP_HOME}

# Prepare some writeable bind-mount points.
FMRIPREP_HOST_CACHE=$FMRIPREP_HOME/.cache/fmriprep
mkdir -p ${FMRIPREP_HOST_CACHE}

# Make sure FS_LICENSE is defined in the container.
mkdir -p $FMRIPREP_HOME/.freesurfer
export SINGULARITYENV_FS_LICENSE=$FMRIPREP_HOME/.freesurfer/license.txt
cp ${LOCAL_FS_LICENSE} ${SINGULARITYENV_FS_LICENSE}

# Designate a templateflow bind-mount point
export SINGULARITYENV_TEMPLATEFLOW_HOME="/templateflow"

# Singularity CMD 
SINGULARITY_CMD="singularity run \
-B ${BIDS_DIR}:/data_dir \
-B ${FMRIPREP_HOME}:/home/fmriprep --home /home/fmriprep --cleanenv \
-B ${FP_OUT_DIR}:/output \
-B ${TEMPLATEFLOW_HOST_HOME}:${SINGULARITYENV_TEMPLATEFLOW_HOME} \
-B ${FMRIPREP_DIR}:/work \
-B ${FS_DIR}:/fsdir \
 ${SINGULARITY_CONTAINER}"

# Remove IsRunning files from FreeSurfer
# find ${FS_DIR}/sub-$PARTICIPANT_ID/ -name "*IsRunning*" -type f -delete

# Compose fMRIPrep command
cmd="${SINGULARITY_CMD} /data_dir /output participant --participant-label $PARTICIPANT_ID \
    -w /work \
    --output-spaces MNI152NLin2009cAsym:res-2 anat fsnative \
    --fs-subjects-dir /fsdir \
    --skip_bids_validation \
    --bids-database-dir /work/first_run/bids_db/ \
    --fs-license-file /home/fmriprep/.freesurfer/license.txt \
    --return-all-components -v \
    --write-graph --notrack \
    --omp-nthreads 4 --nthreads 8 --mem_mb 4000"

# Field map (TODO)
# --use-syn-sdc --force-syn --ignore fieldmaps \

# Append optional args
if [ "$BIDS_FILTER" -eq 1 ]; then
    echo "***Using a BIDS filter**"
    cmd=$cmd" \
    --bids-filter-file /data_dir/bids_filter.json"
fi

if [ "$ANAT_ONLY" -eq 1 ]; then
    echo "***Only running anatomical workflow***"
    cmd=$cmd" \
    --anat-only"
fi

# Setup done, run the command
unset PYTHONPATH
echo ""
echo Commandline: $cmd
echo ""
eval $cmd
exitcode=$?

rm -rf ${FMRIPREP_HOME}
exit $exitcode

echo "Submission finished!"
