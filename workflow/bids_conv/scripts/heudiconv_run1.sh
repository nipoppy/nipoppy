#!/bin/bash

if [ "$#" -ne 10 ]; then
  echo "Please provide MR_PROC_ROOT, participant ID, session ID, datastore dir (in case dicoms are symlinks) \
  and test_run flag"

  echo "Sample cmd: ./heudiconv_run1.sh -m <mr_proc_root> -p <sub-01> -s <01> -d <./> -t 1"
  exit 1
fi

while getopts m:p:s:d:t: flag
do
    case "${flag}" in
        m) MR_PROC_ROOT=${OPTARG};;
        p) PARTICIPANT_ID=${OPTARG};;
        s) SES_ID=${OPTARG};;
        d) DATASTORE=${OPTARG};;
        t) TEST_RUN=${OPTARG};;
    esac
done

# Container
SINGULARITY_IMG="$MR_PROC_ROOT/proc/containers/heudiconv_cb2fd91.sif"
SINGULARITY_PATH=singularity
# SINGULARITY_PATH=/opt/bin/singularity (bic)

if [ "$TEST_RUN" -eq 1 ]; then
    echo "Doing a test run..."
    DICOM_DIR="test_data/dicom/" #Relative to WD (local or singularity)
    BIDS_DIR="test_data/bids/" #Relative to WD (local or singularity)
else
    echo "Doing a real run..."
    DICOM_DIR="dicom/" #Relative to WD (local or singularity)
    BIDS_DIR="bids/" #Relative to WD (local or singularity)
fi

echo "Local WD: ${MR_PROC_ROOT}"
echo "Subject_id: ${PARTICIPANT_ID}, Session_id: ${SES_ID}"

# singularity folders
SINGULARITY_WD=/scratch
SINGULARITY_DICOM_DIR=${SINGULARITY_WD}/${DICOM_DIR}
SINGULARITY_BIDS_DIR=${SINGULARITY_WD}/${BIDS_DIR}

echo "Singularity dicom dir: $SINGULARITY_DICOM_DIR"
echo "Singularity bids dir: $SINGULARITY_BIDS_DIR"

# QPN dicoms are links from bic data server (store).
# So we need to BIND this as well
LOCAL_DATA_STORE=$DATASTORE #"/data" #(bic)
SINGULARITY_DATA_STORE="/data"

# run heudiconv at subject level.
# {subject} is the variable in the heuristics file created for each dataset to filter images during conversion.\

echo "Heudiconv Run1 started..."

$SINGULARITY_PATH run -B ${MR_PROC_ROOT}:${SINGULARITY_WD} \
-B ${LOCAL_DATA_STORE}:${SINGULARITY_DATA_STORE} ${SINGULARITY_IMG} \
heudiconv  \
-d $SINGULARITY_DICOM_DIR/{subject}/* \
-s ${PARTICIPANT_ID} -c none \
-f convertall \
-o ${SINGULARITY_BIDS_DIR} \
--overwrite \
-ss ${SES_ID} \

echo "Heudiconv Run1 finished!"
