#!/bin/bash

while getopts d:p:s:t: flag
do
    case "${flag}" in
        d) MR_PROC_ROOT=${OPTARG};;
        p) PARTICIPANT_ID=${OPTARG};;
        s) SES_ID=${OPTARG};;
        t) TEST_RUN=${OPTARG};;
    esac
done

echo "$MR_PROC_ROOT $PARTICIPANT_ID $SES_ID $TEST_RUN"

if [ "$TEST_RUN" -eq 1 ]; then
    echo "Doing a test run"
fi