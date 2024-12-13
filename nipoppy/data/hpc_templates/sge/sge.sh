#!/bin/bash
#$ -N {{ job_name }}                            # Job name
#$ -cwd                                         # Start job in the current directory
# Output logs to the specified dataset root
#$ -o {{ dataset_root }}/logs/hpc/$JOB_NAME_$JOB_ID.$SGE_TASK_ID.out    # Standard output
#$ -e {{ dataset_root }}/logs/hpc/$JOB_NAME_$JOB_ID.$SGE_TASK_ID.err    # Standard error
{%- if memory_max %}
#$ -l h_vmem={{ memory_max }}G                  # Max memory in GB
{%- endif %}
{%- if run_time_max %}
#$ -l h_rt={{ '%02d:%02d:%02d' % (run_time_max // 60, run_time_max % 60, 0) }}  # Max runtime
{%- endif %}
{%- if account %}
#$ -q {{ account }}                             # Account name (if needed)
{%- endif %}
#$ -t 1-{{ num_tasks }}                         # Specifies the array job range
{%- if task_concurrency %}
#$ -tc {{ task_concurrency }}                    # Limits the maximum number of tasks running at once
{%- else %}
#$ -tc 100                                      # Default concurrency limit
{%- endif %}

# Ensure the logs directory exists
mkdir -p {{ dataset_root }}/logs/hpc

# Change to the desired working directory
cd {{ dataset_root }}/logs/hpc

{{ command }}