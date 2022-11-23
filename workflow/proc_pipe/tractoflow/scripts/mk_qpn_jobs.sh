#!/bin/bash

find /data/pd/qpn/bids -maxdepth 1 -mindepth 1 -type d -name "sub-*" -printf "%f\n" | xargs -n 1 /data/pd/qpn/tractoflow/bin/mk_tracto_job.sh

