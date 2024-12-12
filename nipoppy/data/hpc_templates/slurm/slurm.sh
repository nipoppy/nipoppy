#!/bin/bash
#SBATCH --output={{ dataset_root }}/logs/hpc/%x_%A_%a.out  # Logs directory with job name, job ID, and array task ID
#SBATCH --error={{ dataset_root }}/logs/hpc/%x_%A_%a.err   # Separate error logs
#SBATCH --job-name={{ job_name }}                          # Job name
{%- if account_name %}
#SBATCH --account={{ account_name }}                       # Account name
{%- endif %}
#SBATCH --chdir={{ working_directory }}                    # Change to the specified directory
{%- if cores %}
#SBATCH --cpus-per-task={{ cores }}                        # CPUs per task
{%- endif %}
{%- if run_time_max %}
#SBATCH --time=00:{{ run_time_max }}:00                    # Max run time in mins
{%- endif %}
{%- if memory_max %}
#SBATCH --mem={{ memory_max }}G                            # Max memory in GB
{%- endif %}
{%- if task_concurrency %}
#SBATCH --array=0-{{ num_tasks }}%{{ task_concurrency }}    # Array with dynamic task concurrency
{%- else %}
#SBATCH --array=0-{{ num_tasks }}%100                      # Default to 100 concurrent tasks
{%- endif %}

# Ensure the logs directory exists
mkdir -p {{ dataset_root }}/logs/hpc

# Change to the desired working directory
cd {{ dataset_root }}/logs/hpc

{{ command }}