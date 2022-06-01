#!/bin/bash

if [ "$#" -ne 3 ]; then
  echo "Please provide LOCAL_WD, subject ID and session ID"
  exit 1
fi

LOCAL_WD=$1 #"/data/pd/qpn" (on bic)
subject_id=$2
ses_id=$3

SINGULARITY_IMG="/data/pd/qpn/containers/heudiconv_cb2fd91.sif"
# SINGULARITY_IMG="/home/nikhil/projects/my_containers/heudiconv_cb2fd91.sif"

SINGULARITY_PATH=/opt/bin/singularity #/opt/bin/singularity (bic)

DICOM_DIR="dicom_heudiconv/" #Relative to WD (local or singularity)
BIDS_DIR="bids/" #Relative to WD (local or singularity)

# QPN dicoms are links from bic data server (store).
# So we need to BIND this as well
LOCAL_DATA_STORE="/data" #(bic)
SINGULARITY_DATA_STORE="/data"

echo "Local WD: ${LOCAL_WD}"
echo "Subject_id: ${subject_id}, Session_id: ${ses_id}"

# singularity folders
SINGULARITY_WD=/scratch/
SINGULARITY_OUT_DIR=${SINGULARITY_WD}${BIDS_DIR}

echo "Singularity dicom dir: ${SINGULARITY_WD}/${DICOM_DIR}"
echo "Singularity bids dir: $SINGULARITY_OUT_DIR"

# run heudiconv at subject level.
# {subject} is the variable in the heuristics file created for each dataset to filter images during conversion. (e.g. Heuristics_PPMI_T1.py) 

echo "Heudiconv Run1 started..."

$SINGULARITY_PATH run -B ${LOCAL_WD}:${SINGULARITY_WD} \
-B ${LOCAL_DATA_STORE}:${SINGULARITY_DATA_STORE} ${SINGULARITY_IMG} \
heudiconv  \
-d ${SINGULARITY_WD}/${DICOM_DIR}/{subject}/* \
-s ${subject_id} -c none \
-f convertall \
-o ${SINGULARITY_OUT_DIR} \
--overwrite \
-ss ${ses_id} \

#--grouping studyUID \

echo "Heudiconv Run1 finished!"
