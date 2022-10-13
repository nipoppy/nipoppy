#!/bin/bash

if [ "$#" -ne 14 ]; then
  echo "Please provide DATASET_ROOT, HEUDICONV_IMG, SINGULAIRTY_RUN_CMD, participant ID, session ID, datastore dir (in case dicoms are symlinks) \
  and test_run flag"

  echo "Sample cmd: ./heudiconv_stage_1.sh -d <dataset_root> -h <path_to_heudiconv_img> -r <singularity> -p <MNI01> -s <01> -l <./> -t 1"
  exit 1
fi

while getopts d:i:r:p:s:l:t: flag
do
    case "${flag}" in
        d) DATASET_ROOT=${OPTARG};;
        i) SINGULARITY_IMG=${OPTARG};;
        r) RUN_CMD=${OPTARG};;
        p) PARTICIPANT_ID=${OPTARG};;
        s) SES_ID=${OPTARG};;
        l) DATASTORE=${OPTARG};;
        t) TEST_RUN=${OPTARG};;        
    esac
done

# Container
SINGULARITY_IMG=$SINGULARITY_IMG
SINGULARITY_PATH=$RUN_CMD

if [ "$TEST_RUN" -eq 1 ]; then
    echo "Doing a test run..."
    DICOM_DIR="test_data/dicom/" #Relative to WD (local or singularity)
    BIDS_DIR="test_data/bids/" #Relative to WD (local or singularity)
else
    echo "Doing a real run..."
    DICOM_DIR="dicom/" #Relative to WD (local or singularity)
    BIDS_DIR="bids/" #Relative to WD (local or singularity)
fi

echo "DATASET_ROOT: ${DATASET_ROOT}"
echo "PARTICIPANT_ID: ${PARTICIPANT_ID}, Session_id: ${SES_ID}"

# singularity folders
SINGULARITY_WD=/scratch
SINGULARITY_DICOM_DIR=${SINGULARITY_WD}/${DICOM_DIR}
SINGULARITY_BIDS_DIR=${SINGULARITY_WD}/${BIDS_DIR}

echo "Singularity dicom dir: $SINGULARITY_DICOM_DIR"
echo "Singularity bids dir: $SINGULARITY_BIDS_DIR"

# if mr_proc dicoms are symlinks from some data server
# we need to BIND that location to the container as well 
LOCAL_DATA_STORE=$DATASTORE 
SINGULARITY_DATA_STORE="/data"

# run heudiconv at subject level.
# {subject} is the variable in the heuristics file created for each dataset to filter images during conversion.\

echo "Heudiconv Stage_1 started..."

$SINGULARITY_PATH run -B ${DATASET_ROOT}:${SINGULARITY_WD} \
-B ${LOCAL_DATA_STORE}:${SINGULARITY_DATA_STORE} ${SINGULARITY_IMG} \
heudiconv  \
-d $SINGULARITY_DICOM_DIR/{subject}/* \
-s ${PARTICIPANT_ID} -c none \
-f convertall \
-o ${SINGULARITY_BIDS_DIR} \
--overwrite \
-ss ${SES_ID} \

echo "Heudiconv Stage_1 finished!"