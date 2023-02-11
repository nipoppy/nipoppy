#!/bin/bash

# This is a script to setup dataset directory tree to be processed by mr_proc 
# author: nikhil153
# date: 1 Feb 2022 (last update)

if [ "$#" -ne 2 ]; then
    echo "Please specify local root dir and dataset name to generate mr_proc directory structure"
    exit 1
fi

LOCAL_ROOT=$1
DATASET=$2

DATASET_ROOT=$1/$2

if [ -d $DATASET_ROOT ]; then
    echo "*** dataset root dir: $DATASET_ROOT already exists ***"
    exit 1

else
    echo "--------------------------------------------------"
    echo "*** setting mr_proc root dir at: $DATASET_ROOT ***"
    echo "*** creating sub-dir tree under: $DATASET_ROOT ***"
    echo "--------------------------------------------------"

    mkdir -p $DATASET_ROOT/{scratch,backups,downloads,proc,test_data,tabular,dicom,bids,derivatives,releases}
    mkdir -p $DATASET_ROOT/test_data/{dicom,bids,derivatives,tabular}
    mkdir -p $DATASET_ROOT/tabular/{demographics,assessments}
    mkdir -p $DATASET_ROOT/derivatives/{freesurfer,fmriprep,mriqc,tractoflow}

    mr_proc_manifest=$DATASET_ROOT/tabular/demographics/mr_proc_manifest.csv    
    
    if [ ! -f $mr_proc_manifest ]; then
        echo ""
        echo "initializing mr_proc_manifest.csv"
        echo "participant_id,age,sex,group" > $mr_proc_manifest
    fi
    echo "--------------------------------------------------"
    echo "Need to poulate mandatory recruitment manifest: $mr_proc_manifest"
    echo "--------------------------------------------------"

    global_config=$DATASET_ROOT/proc/global_config.json

    if [ ! -f $global_config ]; then
        echo ""
        echo "copying global config template"
        cp ../workflow/global_configs.json $global_config
    fi
    echo "--------------------------------------------------"
    echo "Need to poulate mandatory global configs for pipeline processing: $global_config"
    echo "--------------------------------------------------"

fi
