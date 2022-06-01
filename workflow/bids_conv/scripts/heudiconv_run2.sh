#!/bin/bash

if [ "$#" -ne 4 ]; then
  echo "Please provide local WD, subject ID, session ID, and Heuristic file path (e.g. Heuristics_qpn.py)"
  exit 1
fi


LOCAL_WD=$1 #"/data/pd/qpn" (on bic)
subject_id=$2
ses_id=$3
HEURISTIC_FILE=$4

SINGULARITY_IMG="/data/pd/qpn/containers/heudiconv_cb2fd91.sif"
# SINGULARITY_IMG="/home/nikhil/projects/my_containers/heudiconv_cb2fd91.sif"
SINGULARITY_PATH=/opt/bin/singularity #(bic)

DICOM_DIR="dicom_heudiconv/" #Relative to WD (local or singularity)
BIDS_DIR="bids/" #Relative to WD (local or singularity)
LOCAL_CODE_DIR="/home/bic/nikhil/QPN_processing/"

# QPN dicoms are links from BIC data server (store).
# So we need to BIND this as well
LOCAL_DATA_STORE="/data"
SINGULARITY_DATA_STORE="/data"

echo "Local WD: ${LOCAL_WD}"
echo "Subject_id: ${subject_id}, Session_id: ${ses_id}"

# singularity folders
SINGULARITY_WD=/scratch/
SINGULARITY_OUT_DIR=${SINGULARITY_WD}${BIDS_DIR}
SINGULARITY_CODE_DIR=${SINGULARITY_WD}QPN_processing

echo "Heudiconv Run2 started..."

# run heudiconv at subject level.
# {subject} is the variable in the heuristics file created for each dataset to filter images during conversion.
# (e.g. Heuristics_PPMI_T1.py) 

$SINGULARITY_PATH run -B ${LOCAL_WD}:${SINGULARITY_WD} \
-B ${LOCAL_CODE_DIR}:${SINGULARITY_CODE_DIR} \
-B ${LOCAL_DATA_STORE}:${SINGULARITY_DATA_STORE} ${SINGULARITY_IMG} \
heudiconv  \
-d ${SINGULARITY_WD}/${DICOM_DIR}/{subject}/* \
-s ${subject_id} -c none \
-f ${SINGULARITY_CODE_DIR}/bids/heuristics/${HEURISTIC_FILE} \
--grouping studyUID \
-c dcm2niix -b --overwrite --minmeta \
-o ${SINGULARITY_OUT_DIR} \
-ss ${ses_id} 

echo "Heudiconv Run2 finishted, conversion complete!"

# --command populate-intended-for \
# TypeError: populate_intended_for() missing 2 required positional arguments: 'matching_parameters' and 'criterion'
# Add below to heuristics file
# POPULATE_INTENDED_FOR_OPTS = {
#         'matching_parameters': ['ImagingVolume', 'Shims'],
#         'criterion': 'Closest'
# }
