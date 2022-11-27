#!/bin/bash

if [ "$#" -ne 3 ]; then
  echo "Please provide global_config, participant_list, session_id"
  exit 1
fi

global_config=$1
participant_list=$2
session_id=$3

n_participants=`cat participant_list | wc -l`
echo "Found $n_participants in the list"
echo ""
for participant_id in `cat participant_list`; do 
    echo "---------------------------------------------------"
    echo "Starting participant: ${participant_id}"
    echo "---------------------------------------------------"
    echo "Starting stage 1"
    python run_bids_conv.py --global_config $global_config \
        --participant_id $participant_id \
        --session_id $session_id \
        --stage 1

    echo "Ending stage 1"
    echo "---------------------------------------------------"
    echo "Starting stage 2"
    python run_bids_conv.py --global_config $global_config \
        --participant_id $participant_id \
        --session_id $session_id \
        --stage 2

    echo "Ending stage 2"
    echo "---------------------------------------------------"
done