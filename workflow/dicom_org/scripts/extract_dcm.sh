#!/bin/bash

# This is a script to extract and rename a subject-level dicom directory from nested tar archives for QPN data
# author: nikhil153
# date: 19 Jan 2022

if [ "$#" -ne 2 ]; then
  echo "Please provide tar file and output dir"
  exit 1
fi

TAR_FILE=$1
OUTPUT_DIR=$2
LOG_FILE=$OUTPUT_DIR/dcm_extract.log

TAR_BASENAME="$(basename -- $TAR_FILE)"

if [ ! -d "./tmp" ]; then
   mkdir ./tmp
fi

mkdir ./tmp/$TAR_BASENAME
cd ./tmp/$TAR_BASENAME

echo "dcm_extract started ..."
echo "extracting tar files"
tar -xf $TAR_FILE
tar -xf *.tar.gz

echo "finding DCM dir" 
DCM_PATH=`find . -name PD*`

if [ -z "$DCM_PATH" ]; then
  
  echo "DCM_DIR not found within $TAR_FILE"
  DCM_DIR=""
  SUB_DIR=""
  N_DCM="0"

  LOG_STR="ERROR: $TAR_FILE, $DCM_DIR, $SUB_DIR, $N_DCM"

else

  DCM_DIR="$(basename -- $DCM_PATH)"
  echo "DCM_DIR: $DCM_DIR"
  
  SUB_DIR=`echo $DCM_DIR | cut -d "_" -f1`

  echo "moving DCM_DIR to ouptut dir: $OUTPUT_DIR" 
  mv $DCM_PATH $OUTPUT_DIR/$SUB_DIR

  N_DCM=`ls $OUTPUT_DIR/$SUB_DIR | wc -l`

  LOG_STR="INFO: $TAR_FILE, $DCM_DIR, $SUB_DIR, $N_DCM"
fi

echo $LOG_STR >> $LOG_FILE
echo "see log file: $LOG_FILE"
cd ../..
echo "dcm_extract completed ..."
echo ""
