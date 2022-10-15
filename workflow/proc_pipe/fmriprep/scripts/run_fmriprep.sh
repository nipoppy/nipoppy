#!/bin/bash

# Author: nikhil153
# Last update: 16 Feb 2022

if [ "$#" -ne 20 ]; then
  echo "Please provide DATASET_ROOT, HEUDICONV_IMG, TEMPLATEFLOW_DIR, SINGULAIRTY_RUN_CMD, PARTICIPANT_ID, SESSION_ID, \
        BIDS_FILTER flag (typically to filter out sessions), ANAT_ONLY flag and TEST_RUN flag"

  echo "Sample cmd: ./run_fmriprep_anat_and_func.sh -d <dataset_root> -h <path_to_fmriprep_img> -r <singularity> \
        -f <path_to_templateflow_dir> -p <MNI01> -s <01> -b 1 -a 1 -t 1"
  exit 1
fi

while getopts d:i:r:f:p:s:b:a:v:t: flag
do
    case "${flag}" in
        d) DATASET_ROOT=${OPTARG};;
        i) SINGULARITY_IMG=${OPTARG};;
        r) RUN_CMD=${OPTARG};; 
        f) TEMPLATEFLOW_DIR=${OPTARG};;         
        p) PARTICIPANT_ID=${OPTARG};;
        s) SESSION_ID=${OPTARG};;
        b) BIDS_FILTER=${OPTARG};;
        a) ANAT_ONLY=${OPTARG};;
        v) VERSION=${OPTARG};;
        t) TEST_RUN=${OPTARG};;
    esac
done

# Container
SINGULARITY_IMG=$SINGULARITY_IMG
SINGULARITY_PATH=$RUN_CMD

# TEMPLATEFLOW
TEMPLATEFLOW_HOST_HOME=$TEMPLATEFLOW_DIR

# FS license.txt path
LOCAL_FS_LICENSE=${DATASET_ROOT}/derivatives/fmriprep/license.txt

if [ "$TEST_RUN" -eq 1 ]; then
    echo "Doing a test run..."
    BIDS_DIR="$DATASET_ROOT/test_data/bids/" #Relative to WD (local or singularity)
    DERIV_DIR="$DATASET_ROOT/test_data/derivatives/fmriprep/$VERSION/"
else
    echo "Doing a real run..."
    BIDS_DIR="$DATASET_ROOT/bids/" #Relative to WD (local or singularity)
    DERIV_DIR="$DATASET_ROOT/derivatives/fmriprep/$VERSION/"
fi

OUT_DIR=${DERIV_DIR}/output

LOG_FILE=${DERIV_DIR}_fmriprep.log
echo "Starting fmriprep proc with container: ${SINGULARITY_IMG}"
echo ""
echo "Using working dir: ${DERIV_DIR} and subject ID: ${PARTICIPANT_ID}"

# Create subject specific dirs
FMRIPREP_HOME=${OUT_DIR}/fmriprep_home_${PARTICIPANT_ID}
echo "Processing: ${PARTICIPANT_ID} with home dir: ${FMRIPREP_HOME}"
mkdir -p ${FMRIPREP_HOME}

LOCAL_FREESURFER_DIR="${OUT_DIR}/freesurfer/ses-${SESSION_ID}"
mkdir -p ${LOCAL_FREESURFER_DIR}

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
-B ${OUT_DIR}:/output \
-B ${TEMPLATEFLOW_HOST_HOME}:${SINGULARITYENV_TEMPLATEFLOW_HOME} \
-B ${DERIV_DIR}:/work \
-B ${LOCAL_FREESURFER_DIR}:/fsdir \
 ${SINGULARITY_IMG}"

# Remove IsRunning files from FreeSurfer
# find ${LOCAL_FREESURFER_DIR}/sub-$PARTICIPANT_ID/ -name "*IsRunning*" -type f -delete

# Compose fMRIPrep command
cmd="${SINGULARITY_CMD} /data_dir /output participant --participant-label $PARTICIPANT_ID \
    -w /work \
    --output-spaces MNI152NLin2009cAsym:res-2 anat fsnative \
    --fs-subjects-dir /fsdir \
    --skip_bids_validation \
    --bids-database-dir /work/first_run/bids_db/
    --fs-license-file /home/fmriprep/.freesurfer/license.txt \
    --return-all-components -v \
    --write-graph --notrack
    --omp-nthreads 4 --nthreads 8 --mem_mb 4000"

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
