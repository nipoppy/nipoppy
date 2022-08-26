#!/bin/bash

# Author: nikhil153
# Last update: 16 Feb 2022

if [ "$#" -ne 10 ]; then
  echo "Please provide DATASET_ROOT, PARTICIPANT_ID, SESSION_ID, BIDS_FILTER (typically to filter out sessions) \
  and TEST_RUN flag"

  echo "Sample cmd: ./run_fmriprep_anat.sh -d <dataset_root> -p <sub-01> -s <01> -b <bids_filter.json> -t 1"
  exit 1
fi

while getopts d:p:s:b:t: flag
do
    case "${flag}" in
        d) DATASET_ROOT=${OPTARG};;
        p) PARTICIPANT_ID=${OPTARG};;
        s) SESSION_ID=${OPTARG};;
        b) BIDS_FILTER=${OPTARG};;
        t) TEST_RUN=${OPTARG};;
    esac
done

# Versions (hardcoded for now)
FMRIPREP_VERSION="20.2.7"
FS_VERSION="6.0.1"

# Container
SINGULARITY_IMG="$DATASET_ROOT/proc/containers/fmriprep_${FMRIPREP_VERSION}.sif"
SINGULARITY_PATH=singularity

# TEMPLATEFLOW
TEMPLATEFLOW_HOST_HOME="$DATASET_ROOT/proc/templateflow"

if [ "$TEST_RUN" -eq 1 ]; then
    echo "Doing a test run..."
    BIDS_DIR="test_data/bids/" #Relative to WD (local or singularity)
    DERIV_DIR="test_data/derivatives/fmriprep/"
else
    echo "Doing a real run..."
    BIDS_DIR="bids/" #Relative to WD (local or singularity)
    DERIV_DIR="derivatives/fmriprep/"
fi

OUT_DIR=${DERIV_DIR}/output

LOG_FILE=${DERIV_DIR}_fmriprep_anat.log
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
cp ${DERIV_DIR}/license.txt ${SINGULARITYENV_FS_LICENSE}

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

# Compose the command line
if [ -f ${BIDS_DIR}/${BIDS_FILTER} ]; then
    echo "Using ${BIDS_FILTER}"
    cmd="${SINGULARITY_CMD} /data_dir /output participant --participant-label $PARTICIPANT_ID \
    -w /work \
    --output-spaces MNI152NLin2009cAsym:res-2 MNI152NLin6Sym:res-1 MNI152Lin:res-1 anat fsnative fsaverage5 \
    --fs-subjects-dir /fsdir \
    --skip_bids_validation \
    --bids-database-dir /work/first_run/bids_db/
    --fs-license-file /home/fmriprep/.freesurfer/license.txt \
    --return-all-components -v \
    --write-graph --notrack \
    --bids-filter-file /data_dir/${BIDS_FILTER} \
    --anat-only" 

else    
    echo "${BIDS_FILTER} not found"

    cmd="${SINGULARITY_CMD} /data_dir /output participant --participant-label $PARTICIPANT_ID \
    -w /work \
    --output-spaces MNI152NLin2009cAsym:res-2 MNI152NLin6Sym:res-1 MNI152Lin:res-1 anat fsnative fsaverage5 \
    --fs-subjects-dir /fsdir \
    --skip_bids_validation \
    --bids-database-dir /work/first_run/bids_db/
    --fs-license-file /home/fmriprep/.freesurfer/license.txt \
    --return-all-components -v \
    --write-graph --notrack \
    --anat-only" 
fi


#--cifti-out 91k" 

# Setup done, run the command
#echo Running task ${SLURM_ARRAY_TASK_ID}
unset PYTHONPATH
echo Commandline: $cmd
eval $cmd
exitcode=$?

# Output results to a table
echo "$PARTICIPANT_ID    ${SLURM_ARRAY_TASK_ID}    $exitcode"
echo Finished tasks ${SLURM_ARRAY_TASK_ID} with exit code $exitcode
rm -rf ${FMRIPREP_HOME}
exit $exitcode

echo "Submission finished!"
